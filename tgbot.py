import aiohttp
import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData

# --- Config ---
try:
    from config import TOKEN, WEATHER_TOKEN
except ImportError:
    TOKEN = os.getenv('TOKEN')
    WEATHER_TOKEN = os.getenv('WEATHER_TOKEN')

NOTES_FILE = 'notes.json'

# --- Bot & Dispatcher ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Callback Data ---
class DeleteCallback(CallbackData, prefix='delete'):
    note_id: int

# --- States ---
class WeatherState(StatesGroup):
    waiting_for_city = State()

class NoteState(StatesGroup):
    waiting_for_note = State()

class DeleteState(StatesGroup):
    waiting_for_delete = State()

class SearchState(StatesGroup):
    waiting_for_query = State()

# --- Keyboard ---
def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🌍 Weather')],
            [KeyboardButton(text='📝 New Note'), KeyboardButton(text='🗑 Delete Note')],
            [KeyboardButton(text='📚 My Notes'), KeyboardButton(text='🔍 Search')],
            [KeyboardButton(text='🕵️ My Profile'), KeyboardButton(text='ℹ️ Help')],
        ],
        resize_keyboard=True
    )

# --- Help ---
@dp.message(F.text == 'ℹ️ Help')
async def show_help(message: types.Message):
    await message.answer(
        '🤖 <b>Commands:</b>\n\n'
        '🌍 /weather (city) — weather\n'
        '📝 /note (text) — save note\n'
        '📚 /all_notes — show notes\n'
        '🗑 /delete (number) — delete note\n'
        '🔍 /find (query) — search everywhere\n'
        '🕵️/My_Profile — your info\n'
        '/start — main menu',
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

# --- Weather ---
async def get_weather(city: str) -> str:
    url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'appid': WEATHER_TOKEN, 'units': 'metric', 'lang': 'en'}
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return (
                    f'🌍 {city.title()}:\n'
                    f'🌡 {data["main"]["temp"]}°C (feels like {data["main"]["feels_like"]}°C)\n'
                    f'☁️ {data["weather"][0]["description"].capitalize()}'
                )
            return f'❌ City not found.' if resp.status == 404 else f'⚠️ Error: {resp.status}'

# --- Notes ---
def load_notes() -> list:
    if not os.path.exists(NOTES_FILE):
        return []
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_notes(notes: list) -> None:
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

# --- Unified Search ---
async def search_everywhere(query: str) -> str:
    username = query.lower().replace(' ', '_')
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    # 1. Check platforms
    platform_results = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), headers=headers) as session:
        for name, domain in [
            ('VK', f'https://vk.com/{username}'),
            ('GitHub', f'https://github.com/{username}'),
            ('Reddit', f'https://reddit.com/user/{username}'),
            ('Twitter/X', f'https://x.com/{username}'),
        ]:
            try:
                async with session.get(domain, timeout=5, allow_redirects=True) as resp:
                    if resp.status == 200:
                        platform_results.append(f'• <a href="{domain}">{name}</a>')
            except:
                pass
    
    # 2. Search via SearXNG, fallback to Wikipedia
    google_results = []
    
    # Try SearXNG first
    for server in [
        'https://search.sapti.me/search',
        'https://searx.tiekoetter.com/search',
    ]:
        try:
            params = {'q': query, 'format': 'json', 'pageno': 1}
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), headers=headers) as session:
                async with session.get(server, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get('results', [])
                        if results:
                            for item in results[:3]:
                                title = item.get('title', '')[:100]
                                link = item.get('url', '')
                                if title and link:
                                    google_results.append(f'• <a href="{link}">{title}</a>')
                            break
        except:
            pass
    
    # Fallback to Wikipedia
    if not google_results:
        try:
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'format': 'json',
                'srlimit': 3,
            }
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), headers=headers) as session:
                async with session.get('https://en.wikipedia.org/w/api.php', params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get('query', {}).get('search', [])[:3]:
                            title = item['title']
                            link = f'https://en.wikipedia.org/wiki/{title.replace(" ", "_")}'
                            snippet = item.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '')[:100]
                            google_results.append(f'• <a href="{link}">{title}</a> — {snippet}...')
        except:
            pass
    
    # 3. Build result
    result = ''
    if platform_results:
        result += '<b>🔗 Profiles found:</b>\n' + '\n'.join(platform_results) + '\n'
    if google_results:
        if result:
            result += '\n'
        result += '<b>🔍 Web search:</b>\n' + '\n'.join(google_results)
    
    return result if result else '❌ Nothing found.'

# --- Handlers ---
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        f'Hello, {message.from_user.first_name}! Use buttons or commands.',
        reply_markup=get_main_keyboard()
    )

@dp.message(Command('My_Profile'))
@dp.message(F.text == '🕵️ My Profile')
async def show_profile(message: types.Message):
    user = message.from_user
    await message.answer(
        f'🪪 <b>Profile:</b>\n'
        f'ID: <code>{user.id}</code>\n'
        f'Name: {user.first_name or "?"} {user.last_name or ""}\n'
        f'Username: @{user.username or "none"}\n'
        f'Language: {user.language_code or "?"}',
        parse_mode='HTML'
    )

# --- Weather Handlers ---
@dp.message(Command('weather'))
async def cmd_weather(message: types.Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        wt = await get_weather(parts[1])
        await message.answer(wt, reply_markup=get_main_keyboard())
        return
    await state.set_state(WeatherState.waiting_for_city)
    await message.answer('Enter city:', reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == '🌍 Weather')
async def ask_city(message: types.Message, state: FSMContext):
    await state.set_state(WeatherState.waiting_for_city)
    await message.answer('Enter city:', reply_markup=ReplyKeyboardRemove())

@dp.message(WeatherState.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    await message.answer(await get_weather(message.text.strip()), reply_markup=get_main_keyboard())
    await state.clear()

# --- Search Handlers ---
@dp.message(Command('find'))
async def cmd_find(message: types.Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        query = parts[1]
        msg = await message.answer(f'🔍 Searching for "{query}"...')
        result = await search_everywhere(query)
        await msg.edit_text(result, parse_mode='HTML', disable_web_page_preview=True)
        await message.answer('What next?', reply_markup=get_main_keyboard())
        return
    await state.set_state(SearchState.waiting_for_query)
    await message.answer('Enter name or username:', reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == '🔍 Search')
async def start_search(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer('Enter name or username:', reply_markup=ReplyKeyboardRemove())

@dp.message(SearchState.waiting_for_query)
async def process_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    msg = await message.answer(f'🔍 Searching for "{query}"...')
    result = await search_everywhere(query)
    await msg.edit_text(result, parse_mode='HTML', disable_web_page_preview=True)
    await state.clear()
    await message.answer('What next?', reply_markup=get_main_keyboard())

# --- Note Handlers ---
@dp.message(Command('note'))
async def cmd_note(message: types.Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        notes = load_notes()
        notes.append(parts[1])
        save_notes(notes)
        await message.answer(f'✅ Saved ({len(notes)} notes)', reply_markup=get_main_keyboard())
        return
    await state.set_state(NoteState.waiting_for_note)
    await message.answer('Enter note text:', reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == '📝 New Note')
async def ask_note(message: types.Message, state: FSMContext):
    await state.set_state(NoteState.waiting_for_note)
    await message.answer('Enter note text:', reply_markup=ReplyKeyboardRemove())

@dp.message(NoteState.waiting_for_note)
async def save_new_note(message: types.Message, state: FSMContext):
    notes = load_notes()
    notes.append(message.text.strip())
    save_notes(notes)
    await message.answer(f'✅ Saved ({len(notes)} notes)', reply_markup=get_main_keyboard())
    await state.clear()

@dp.message(Command('all_notes'))
@dp.message(F.text == '📚 My Notes')
async def show_notes(message: types.Message):
    notes = load_notes()
    if not notes:
        await message.answer('No notes yet.', reply_markup=get_main_keyboard())
        return
    for i, note in enumerate(notes, 1):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='❌', callback_data=DeleteCallback(note_id=i).pack())
        ]])
        await message.answer(f'{i}. {note}', reply_markup=keyboard)

# --- Delete Handlers ---
@dp.message(Command('delete'))
@dp.message(F.text == '🗑 Delete Note')
async def ask_delete(message: types.Message, state: FSMContext):
    notes = load_notes()
    if not notes:
        await message.answer('No notes.', reply_markup=get_main_keyboard())
        return
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        try:
            i = int(parts[1])
            if 1 <= i <= len(notes):
                deleted = notes.pop(i - 1)
                save_notes(notes)
                await message.answer(f'✅ Deleted: {deleted}', reply_markup=get_main_keyboard())
                return
        except ValueError:
            pass
    for i, note in enumerate(notes, 1):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='❌', callback_data=DeleteCallback(note_id=i).pack())
        ]])
        await message.answer(f'{i}. {note}', reply_markup=keyboard)
    await state.set_state(DeleteState.waiting_for_delete)
    await message.answer('Enter note number to delete:', reply_markup=ReplyKeyboardRemove())

@dp.message(DeleteState.waiting_for_delete)
async def delete_note_by_number(message: types.Message, state: FSMContext):
    try:
        i = int(message.text.strip())
        notes = load_notes()
        if 1 <= i <= len(notes):
            deleted = notes.pop(i - 1)
            save_notes(notes)
            await message.answer(f'✅ Deleted: {deleted}', reply_markup=get_main_keyboard())
            await state.clear()
            return
    except ValueError:
        pass
    await message.answer('❌ Invalid number.', reply_markup=ReplyKeyboardRemove())

@dp.callback_query(DeleteCallback.filter())
async def delete_inline(callback: types.CallbackQuery, callback_data: DeleteCallback):
    notes = load_notes()
    i = callback_data.note_id
    if 1 <= i <= len(notes):
        deleted = notes.pop(i - 1)
        save_notes(notes)
        await callback.message.delete()
        await callback.message.answer(f'✅ Deleted: {deleted}', reply_markup=get_main_keyboard())
        await callback.answer('Deleted!')
    else:
        await callback.answer('Not found.', show_alert=True)

# --- Echo ---
@dp.message()
async def echo(message: types.Message):
    await message.answer('Use /help for commands.')

# --- Main ---
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())