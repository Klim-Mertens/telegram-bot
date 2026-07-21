import aiohttp

import asyncio
import os
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import json
from aiogram import Bot, Dispatcher, types,F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup 
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup , InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData




try:
    from config import TOKEN, WEATHER_TOKEN
except ImportError:
    TOKEN = os.getenv('TOKEN')
    WEATHER_TOKEN = os.getenv('WEATHER_TOKEN')

NOTES_FILE = 'notes.json'


bot= Bot(token=TOKEN)
dp=Dispatcher()

class DeleteCallback(CallbackData, prefix= 'deleta'):
    note_id: int


class WeatherState(StatesGroup):
    waiting_for_city = State()

class NoteState(StatesGroup):
    waiting_for_note = State()

class DeleteState(StatesGroup):
    waiting_for_delete = State()



def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🌍 Weather')],
            [
                KeyboardButton(text='📝 New Note'),
                KeyboardButton(text='🗑 Delete Note')
            ],
            [
                KeyboardButton(text='📚 My Notes'),
                KeyboardButton(text='ℹ️ Help')
            ],
        ],
        resize_keyboard=True
    )
    return kb



@dp.message(F.text == 'ℹ️ Help')
async def show_help(message: types.Message):
    await message.answer(
        '🤖 <b>What I can do:</b>\n\n'
        '🌍 <b>Weather</b> — press button and choose city.\n'
        '📝 <b>New Note</b> — press button and write note text.\n'
        '🗑 <b>Delete Note</b> — press button and choose number.\n'
        '📚 <b>My Notes</b> — show your notes.\n\n'
        '<i>OR you can use commands:</i>\n'
        '/weather (city) — show weather in city.\n'
        '/note (text) — save note.\n'
        '/all_notes — show all your notes.\n'
        '/delete (number) — delete note.\n'
        '/start — reset bot and show main menu.',
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )



async def get_weather(city:str) -> str:
    url=f"https://api.openweathermap.org/data/2.5/weather"
    params={
        'q':city,
        'appid':WEATHER_TOKEN,
        'units':'metric',
        'lang':'ru',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url,params=params) as response:
            if response.status==200:
                data=await response.json()
                temp=data['main']['temp']
                fl=data['main']['feels_like']
                des=data['weather'][0]['description']
                return(
                    f'Weater in city {city.title()}:\n'
                    f'Temperature: {temp} °C feels like {fl} °C\n'
                    f'Description: {des.capitalize()}'
                )
            elif response.status==404:
                return f'City {city} was not found. Try another city'
            else:
                return f'Error type :{response.status}'

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    un=message.from_user.first_name
    keyboard=get_main_keyboard()
    await message.answer(

        f'Hallo,{un}! Write something and i will repeat it for you\n'
        f'Or you can write: \n/weather (city) and i will show you weather \n'
        f'/note (text) and i will save it for you\n'
        f'/all_notes and i will show you all your notes\n'
        f'/delete (number) and i will delete your note\n'
        f'Use buttons or commands, for help press button ℹ️ Help',
        reply_markup=keyboard
        )

@dp.message(F.text == '🌍 Weather')
async def ask_city(message: types.Message,state: FSMContext):
    await state.set_state(WeatherState.waiting_for_city)
    await message.answer(
        'Please, choose City\n' \
        'example:Moscow',   
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.text == '📝 New Note')
async def ask_note_text(message: types.Message,state: FSMContext):
    await state.set_state(NoteState.waiting_for_note)
    await message.answer(
        'Write note text\n'
        'example: Buy Milk',
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.text == '🗑 Delete Note')
async def ask_delete_number(message: types.Message,state:FSMContext):
    notes = load_notes()
    if not notes:
        await message.answer(
            'You have no notes to delete.',
            reply_markup=get_main_keyboard()
            )
        return
    for i,note in enumerate(notes,1):
        keyboard= InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f'🗑 Delete #{i}',
                callback_data=DeleteCallback(note_id=i).pack()
            )]
        ])
        await message.answer(f'{i}.{note}',reply_markup=keyboard)
    await message.answer(
        'Choose note you want to delete or write number',
        reply_markup= get_main_keyboard()
    )
    await state.set_state(DeleteState.waiting_for_delete)


def load_notes() -> list:
    if os.path.exists(NOTES_FILE)==0:
        return[]
    with open(NOTES_FILE,'r',encoding='utf-8')as f:
        return json.load(f)

def save_notes(notes:list)-> None:
    with open(NOTES_FILE,'w',encoding='utf-8')as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

@dp.message(Command('note'))
async def cmd_note(message: types.Message):
    text=message.text.strip()
    parts=text.split(maxsplit=1)
    if len(parts)==1:
        await message.answer(
            'Write note text\n' \
            'example: /note Buy Milk'
        )
        return
    note_text=parts[1]
    notes= load_notes()
    notes.append(note_text)
    save_notes(notes)
    await message.answer(
        f'Note was added! You have {len(notes)} note(s):\n'
        f'added note: {note_text}'
    )

@dp.message(F.text=='📚 My Notes')
async def show_my_notes(message: types.Message):
    notes= load_notes()
    if not notes:
        await message.answer(
            'You have NO notes',
            reply_markup=get_main_keyboard()
        )
        return
    for i, note in enumerate(notes,1):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f' Delete #{i}',
                callback_data=DeleteCallback(note_id=i).pack()
            )]

        ])
        await message.answer(f'{i}.{note}',reply_markup=keyboard)


@dp.message(Command('all_notes'))
async def cmd_all_notes(message:types.Message):
    notes= load_notes()
    if notes==0:
        await message.answer('You have NO notes',reply_markup=get_main_keyboard())
        return
    for i,note in enumerate(notes,1):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f'🗑 Delete #{i}',
                callback_data=DeleteCallback(note_id=i).pack()
            )]
        ])
        await message.answer(f'{i}.{note}',reply_markup=keyboard)



@dp.message(Command('delete'))
async def cmd_delete(message:types.Message):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts)==1:
        await message.answer(
            'Choose number of note, that have to be deleted\n'
            'example: /delete 9387654567'
            )
        return
    try:
        index=int(parts[1])
    except ValueError:
        await message.answer('Number have to be a number(not letter)\n'
        'example: /delete 987656')
        return
    notes= load_notes()
    if index<1 or index>len(notes):
        await message.answer(f'There is no note with this number\n'
                             f'You have only {len(notes)} notes')
        return
    deleted_note= notes.pop(index-1)
    save_notes(notes)
    await message.answer(f'You deleted note:{deleted_note}')



@dp.message(Command('weather'))
async def cmd_weather(message:types.Message):
    text=message.text.strip()
    parts=text.split(maxsplit=1)
    if len(parts) ==1:
        await message.answer(
            'Please, choose City\n' \
            'example: /weather Moscow'
        )
        return
    city=parts[1]
    await message.answer(f'Finding weather in {city}...')
    wt=await get_weather(city)
    await message.answer(wt)


@dp.message(WeatherState.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    city= message.text.strip()
    await message.answer(f'Finding weather in {city}...')
    wt=await get_weather(city)
    await message.answer(wt,reply_markup=get_main_keyboard())
    await state.clear()
@dp.message(NoteState.waiting_for_note)
async def process_note_text(message:types.Message, state: FSMContext):
    note_text = message.text.strip()
    notes = load_notes()
    notes.append(note_text)
    save_notes(notes)
    await message.answer(
        f'✅ Notes added! You have {len(notes)} notes)\n'
        f'📌 {note_text}',
        reply_markup=get_main_keyboard()
    )
    await state.clear()
@dp.message(DeleteState.waiting_for_delete)
async def process_delete_number(message: types.Message, state: FSMContext):
    text= message.text.strip()
    try:
        index= int(text)
    except ValueError:
        await message.answer(
            '❌ Number have to be a number(not letter)\n'
            'example: /delete 987656',
            reply_markup=ReplyKeyboardRemove()
        )
        return
    notes= load_notes()
    if index<1 or index> len(notes):
        await message.answer(
            f'❌ There is no note with this number\n'
            f'You have only {len(notes)} notes',
            reply_markup=ReplyKeyboardRemove()
        )
        return
    delete_note=notes.pop(index-1)
    save_notes(notes)
    await message.answer(
        f'✅ You deleted note: {delete_note}',
        reply_markup=get_main_keyboard()
    )
    await state.clear()


@dp.callback_query(DeleteCallback.filter())
async def delete_note_inline(callback: types.CallbackQuery, callback_data: DeleteCallback):
    note_id=callback_data.note_id
    notes = load_notes()
    if note_id < 1  or note_id > len(notes):
        await callback.answer(
            '❌ There is no note with this number',
            show_alert = True)
        return
    delete_note = notes.pop(note_id -1 )
    save_notes(notes)
    await callback.message.delete()
    await callback.message.answer(
        f'✅ You deleted note: {delete_note}',
        reply_markup= get_main_keyboard()
    )
    await callback.answer('✅Deleted!')

@dp.message()
async def echo(mes: types.Message):
    await mes.answer(f"You wrote:{mes.text}")
async def main():
    await dp.start_polling(bot)
if __name__=='__main__':
    asyncio.run(main())
    
