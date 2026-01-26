
import tkinter as tk
from tkinter import filedialog, messagebox
import shutil, os, re, sys, tempfile, configparser, subprocess
from datetime import datetime

# --- Константи ---
LOG_FOLDER = os.path.join(tempfile.gettempdir(), "Tool box", "files")
HISTORY_FILE = os.path.join(LOG_FOLDER, "history.txt")
PROFILES_FILE = os.path.join(LOG_FOLDER, "profiles.ini")
NUM_PROFILES = 8

# --- Глобальні змінні ---
found_files = []
copied_files = []
current_folder = ""
current_dest_folder = ""
selected_operation = None  # операція вибрана з історії для збереження у профіль
profiles = {}  # зчитані профілі 

# ====================== ФУНКЦІЇ ======================



def ensure_log_folder():
    os.makedirs(LOG_FOLDER, exist_ok=True)

def get_temp_folder():
    date_str = datetime.now().strftime("%Y-%m-%d")
    temp_folder = os.path.join(LOG_FOLDER, date_str)
    os.makedirs(temp_folder, exist_ok=True)
    return temp_folder

def center_window(win, width=None, height=None, parent=None):
    """
    Центрує вікно win на екрані або відносно parent (якщо вказаний).
    Якщо width і height не задані, використовується поточний розмір вікна.
    """
    win.update_idletasks()

    # Визначаємо розміри вікна
    if width is None:
        width = win.winfo_width()
    if height is None:
        height = win.winfo_height()

    # Центрування відносно батьківського вікна або екрану
    if parent:
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w // 2) - (width // 2)
        y = parent_y + (parent_h // 2) - (height // 2)
    else:
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)

    win.geometry(f"{width}x{height}+{x}+{y}")


def get_next_available_name(folder, filename):
    name, ext = os.path.splitext(filename)
    pattern = re.compile(rf"^{re.escape(name)}_(\d+){re.escape(ext)}$")
    max_counter = 0
    for f in os.listdir(folder):
        match = pattern.match(f)
        if match:
            num = int(match.group(1))
            if num > max_counter:
                max_counter = num
    return f"{name}_{max_counter + 1}{ext}"

# ----------------- Історія -----------------

def add_to_history(files, src_folder, dest_folder):
    ensure_log_folder()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    files_paths = ";".join(files)
    record = f"{date_str} | src={src_folder} | files={files_paths} | dest={dest_folder}\n"
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(record)
    refresh_history_listbox()

def parse_history_line(line):
    line = line.strip()
    m = re.match(r'^(.*?)\s*\|\s*src=(.*?)\s*\|\s*files=(.*?)\s*\|\s*dest=(.*)$', line)
    if m:
        timestamp = m.group(1).strip()
        src = m.group(2).strip()
        files_str = m.group(3).strip()
        dest = m.group(4).strip()
        files = [p for p in files_str.split(";") if p]
        return {"timestamp": timestamp, "src": src, "files": files, "dest": dest}
    m2 = re.match(r'^(.*?):\s*(.*?)\s*->\s*(.*)$', line)
    if m2:
        timestamp = m2.group(1).strip()
        names = [n.strip() for n in m2.group(2).split(",") if n.strip()]
        dest = m2.group(3).strip()
        return {"timestamp": timestamp, "src": None, "files": names, "dest": dest}
    return {"timestamp": "", "src": None, "files": [], "dest": "", "raw": line}

def refresh_history_listbox():
    listbox_history.delete(0, tk.END)
    if not os.path.exists(HISTORY_FILE):
        return
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-50:]:
        parsed = parse_history_line(line)
        if parsed.get("raw"):
            display = parsed["raw"]
        else:
            timestamp = parsed.get("timestamp", "")
            files = parsed.get("files", [])
            dest = parsed.get("dest", "")
            short_names = ", ".join(os.path.basename(p) for p in files[:3])
            if len(files) > 3:
                short_names += f" +{len(files)-3}"
            display = f"{timestamp}: {short_names} -> {dest}"
        listbox_history.insert(tk.END, display)

# ----------------- Профілі -----------------

def load_profiles():
    global profiles
    ensure_log_folder()
    profiles = {}
    config = configparser.ConfigParser()
    if os.path.exists(PROFILES_FILE):
        config.read(PROFILES_FILE, encoding='utf-8')
        for i in range(NUM_PROFILES):
            section = f"Profile{i+1}"
            if section in config:
                src = config[section].get('src', '')
                dest = config[section].get('dest', '')
                files = config[section].get('files', '')
                files_list = [p for p in files.split(';') if p]
                profiles[i] = {'src': src, 'dest': dest, 'files': files_list}
            else:
                profiles[i] = None
    else:
        for i in range(NUM_PROFILES):
            profiles[i] = None

def save_profiles_to_file():
    config = configparser.ConfigParser()
    for i in range(NUM_PROFILES):
        section = f"Profile{i+1}"
        config[section] = {}
        p = profiles.get(i)
        if p:
            config[section]['src'] = p.get('src','')
            config[section]['dest'] = p.get('dest','')
            config[section]['files'] = ";".join(p.get('files',[]))
    with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

def save_profile_at_index(idx):
    global selected_operation
    if not selected_operation:
        messagebox.showwarning("Помилка", "Спочатку виберіть операцію в історії (подвійний клік).")
        return
    profiles[idx] = {'src': selected_operation.get('src'),
                     'dest': selected_operation.get('dest'),
                     'files': selected_operation.get('files')}
    save_profiles_to_file()
    update_profile_buttons()
    messagebox.showinfo("Успіх", f"Операцію збережено в профіль #{idx+1}")
    # Скидаємо вибір після збереження
    selected_operation = None

def load_profile_at_index(idx):
    p = profiles.get(idx)
    if not p:
        messagebox.showinfo("Пусто", f"Профіль #{idx+1} порожній.")
        return
    src = p.get('src')
    files = p.get('files', [])
    dest = p.get('dest')
    if not src or not files or not dest:
        messagebox.showerror("Помилка", "Профіль містить неповні дані.")
        return
    refresh_file_list(src)
    temp_folder = get_temp_folder()
    global copied_files
    copied_files.clear()
    for fp in files:
        if os.path.exists(fp) and os.path.isfile(fp):
            filename = os.path.basename(fp)
            temp_path = os.path.join(temp_folder, filename)
            # видаляємо перевірку і get_next_available_name()
            shutil.copy(fp, temp_path)
            copied_files.append(temp_path)
        else:
            candidate = os.path.join(src, os.path.basename(fp))
            if os.path.exists(candidate) and os.path.isfile(candidate):
                filename = os.path.basename(candidate)
                temp_path = os.path.join(temp_folder, filename)
                if os.path.exists(temp_path):
                    temp_path = os.path.join(temp_folder, get_next_available_name(temp_folder, filename))
                shutil.copy(candidate, temp_path)
                copied_files.append(temp_path)
            else:
                messagebox.showerror("Помилка", f"Не знайдено файл: {os.path.basename(fp)}\nПапка {src} відкрита, знайдіть самі.")
    listbox_temp_files.delete(0, tk.END)
    for f in copied_files:
        listbox_temp_files.insert(tk.END, os.path.basename(f))
    refresh_dest_list(dest)
    messagebox.showinfo("Готово", f"Профіль #{idx+1} завантажено. Залишилося натиснути 'Запуск операції'.")

# ----------------- GUI: кнопки профілів -----------------

def on_profile_button(idx):
    global selected_operation
    if selected_operation:
        if profiles.get(idx):
            if messagebox.askyesno("Питання", f"Профіль #{idx+1} вже містить операцію. Замінити?"):
                save_profile_at_index(idx)
        else:
            save_profile_at_index(idx)
    else:
        load_profile_at_index(idx)

def update_profile_buttons():
    for i, btn in enumerate(profile_buttons):
        p = profiles.get(i)
        if p:
            display = os.path.basename(p.get('dest','')) or f"{i+1}"
            btn.config(text=display)
        else:
            btn.config(text=f"П{i+1}")

# ====================== Основні функції ======================

def refresh_file_list(folder):
    global found_files, current_folder
    found_files.clear()
    listbox_main.delete(0, tk.END)
    current_folder = folder
    try:
        items = os.listdir(folder)
        folders = [i for i in items if os.path.isdir(os.path.join(folder, i))]
        files = [i for i in items if os.path.isfile(os.path.join(folder, i))]
        folders.sort(key=str.lower)
        files.sort(key=str.lower)
        for item in folders + files:
            full_path = os.path.join(folder, item)
            found_files.append(full_path)
            display_name = f"📁 {item}" if os.path.isdir(full_path) else f"📄 {item}"
            listbox_main.insert(tk.END, display_name)
    except Exception as e:
        messagebox.showerror("Помилка", str(e))
    path_entry.delete(0, tk.END)
    path_entry.insert(0, folder)
    path_label.config(text=f"Папка пошуку: {folder}")

def on_item_double_click(event):
    try:
        index = listbox_main.curselection()[0]
        path = found_files[index]
        if os.path.isdir(path):
            refresh_file_list(path)
        else:
            copy_file_from_list()
    except Exception:
        pass

def open_path_from_entry():
    path = path_entry.get().strip()
    if not path or not os.path.isdir(path):
        messagebox.showerror("Помилка", "Введіть існуючу папку!")
        return
    refresh_file_list(path)

def open_search_window():
    folder = filedialog.askdirectory(title="Оберіть папку для пошуку")
    if folder:
        refresh_file_list(folder)

def go_back_folder():
    global current_folder
    if not current_folder: return
    parent = os.path.dirname(current_folder)
    if parent == current_folder or parent == "":
        messagebox.showinfo("Інформація", "Ви вже у кореневій папці.")
        return
    refresh_file_list(parent)

def copy_file_from_list():
    global copied_files
    indices = listbox_main.curselection()
    if not indices:
        messagebox.showwarning("Помилка", "Оберіть файл(и) зі списку!")
        return
    temp_folder = get_temp_folder()
    files_to_copy = [found_files[i] for i in indices if os.path.isfile(found_files[i])]
    for file_path in files_to_copy:
        filename = os.path.basename(file_path)
        temp_path = os.path.join(temp_folder, filename)
        # ТУТ БІЛЬШЕ НЕ РОБИМО get_next_available_name()
        shutil.copy(file_path, temp_path)
        copied_files.append(temp_path)
    listbox_temp_files.delete(0, tk.END)
    for f in copied_files:
        listbox_temp_files.insert(tk.END, os.path.basename(f))
    names = "\n".join(os.path.basename(f) for f in copied_files)
    messagebox.showinfo("Успіх", f"Файли скопійовано у тимчасову папку:\n{names}")


def on_temp_file_double_click(event):
    try:
        index = listbox_temp_files.curselection()[0]
        file_path = copied_files[index]
        if os.path.exists(file_path):
            if sys.platform.startswith('win'):
                os.startfile(file_path)
            elif sys.platform.startswith('darwin'):
                subprocess.call(['open', file_path])
            else:  # Linux/Unix
                subprocess.call(['xdg-open', file_path])
        else:
            messagebox.showerror("Помилка", f"Файл не знайдено:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Помилка", str(e))
        
def clear_temp_files_list():
    global copied_files
    if not copied_files:
        messagebox.showinfo("Інформація", "Список тимчасових файлів порожній.")
        return
    if messagebox.askyesno("Підтвердження", "Ви впевнені, що хочете очистити список скопійованих файлів?"):
        copied_files.clear()
        listbox_temp_files.delete(0, tk.END)

def remove_selected_temp_files():
    global copied_files
    selected_indices = listbox_temp_files.curselection()
    if not selected_indices:
        messagebox.showwarning("Помилка", "Оберіть файл(и), які хочете видалити зі списку.")
        return
    for index in reversed(selected_indices):  # видаляємо з кінця, щоб індекси не зміщувались
        del copied_files[index]
        listbox_temp_files.delete(index)


# --- Вставка ---

def refresh_dest_list(folder):
    global current_dest_folder
    current_dest_folder = folder
    listbox_dest.delete(0, tk.END)
    try:
        items = [i for i in os.listdir(folder) if os.path.isdir(os.path.join(folder, i))]
        items.sort(key=str.lower)
        for i in items:
            listbox_dest.insert(tk.END, f"📁 {i}")
    except Exception as e:
        messagebox.showerror("Помилка", str(e))
    dest_entry.delete(0, tk.END)
    dest_entry.insert(0, folder)

def refresh_dest_path():
    folder = dest_entry.get().strip()
    if not folder or not os.path.isdir(folder):
        messagebox.showerror("Помилка", "Вкажіть існуючу папку для вставлення!")
        return
    refresh_dest_list(folder)

def select_destination_folder():
    folder = filedialog.askdirectory(title="Оберіть папку для вставлення")
    if folder:
        refresh_dest_list(folder)

def dest_go_back():
    global current_dest_folder
    if not current_dest_folder: return
    parent = os.path.dirname(current_dest_folder)
    if parent == current_dest_folder or parent == "":
        messagebox.showinfo("Інформація", "Ви вже у кореневій папці.")
        return
    refresh_dest_list(parent)

def on_dest_double_click(event):
    try:
        index = listbox_dest.curselection()[0]
        folder = os.path.join(current_dest_folder, listbox_dest.get(index)[2:])
        refresh_dest_list(folder)
    except Exception:
        pass
    
def ask_replace_or_rename(filename, multiple=False):
    """
    Повертає кортеж (choice, apply_to_all)
    choice: "replace", "rename", "cancel"
    apply_to_all: True/False
    """
    result = {"choice": "cancel", "apply_to_all": False}

    def on_confirm():
        selected = var.get()
        result["choice"] = "replace" if selected == 1 else "rename"
        result["apply_to_all"] = chk_var.get()
        dialog.destroy()

    dialog = tk.Toplevel(root)
    dialog.title("Файл існує")
    dialog.resizable(False, False)
    center_window(dialog, 320, 200, parent=root)  # центр відносно головного вікна
    dialog.grab_set()

    lbl = tk.Label(dialog, text=f"Файл '{filename}' вже існує у цільовій папці.\nЩо робимо?", wraplength=380)
    lbl.pack(pady=10)

    var = tk.IntVar(value=1)
    rb1 = tk.Radiobutton(dialog, text="Замінити", variable=var, value=1)
    rb2 = tk.Radiobutton(dialog, text="Перейменувати", variable=var, value=2)
    rb1.pack(anchor="w", padx=20)
    rb2.pack(anchor="w", padx=20)

    chk_var = tk.BooleanVar(value=False)
    if multiple:
        chk = tk.Checkbutton(dialog, text="Підтвердити для всіх файлів", variable=chk_var)
        chk.pack(pady=10)

    btn = tk.Button(dialog, text="Підтвердити", command=on_confirm, width=15)
    btn.pack(pady=10)

    dialog.wait_window()  # чекаємо поки користувач закриє вікно
    return result["choice"], result["apply_to_all"]

def run_operation():
    global copied_files, current_dest_folder
    if not copied_files:
        messagebox.showwarning("Помилка", "Спочатку скопіюйте файл(и)!")
        return
    if not current_dest_folder:
        messagebox.showwarning("Помилка", "Вкажіть куди вставляти!")
        return

    apply_to_all = False
    last_choice = None
    for temp_file_path in copied_files:
        filename = os.path.basename(temp_file_path)
        dest_file = os.path.join(current_dest_folder, filename)

        if os.path.exists(dest_file):
            if apply_to_all and last_choice:
                choice = last_choice
            else:
                choice, apply_all = ask_replace_or_rename(filename, multiple=len(copied_files) > 1)
                if apply_all:
                    apply_to_all = True
                    last_choice = choice

            if choice == "replace":
                shutil.copy(temp_file_path, dest_file)
            elif choice == "rename":
                new_name = get_next_available_name(current_dest_folder, filename)
                dest_file = os.path.join(current_dest_folder, new_name)
                shutil.copy(temp_file_path, dest_file)
            else:  # cancel
                continue
        else:
            shutil.copy(temp_file_path, dest_file)

    messagebox.showinfo("Готово", f"Вставлено {len(copied_files)} файл(ів) у {current_dest_folder}")
    original_files = [os.path.join(current_folder, os.path.basename(f)) for f in copied_files]
    add_to_history(original_files, current_folder, current_dest_folder)
    refresh_file_list(current_dest_folder)
    listbox_temp_files.delete(0, tk.END)
    copied_files.clear()
    
# --- Історія: подвійний клік ---
def on_history_double_click(event):
    global selected_operation
    try:
        index = listbox_history.curselection()[0]
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if not lines:
            return
        lines_to_show = lines[-50:]
        line = lines_to_show[index]
        parsed = parse_history_line(line)
        selected_operation = parsed
        messagebox.showinfo("Операція вибрана", f"Вибрано операцію:\n{os.path.basename(parsed.get('dest',''))} з {len(parsed.get('files',[]))} файлів.\nТепер натисніть кнопку профілю щоб зберегти.")
    except Exception as e:
        print(e)

# ====================== GUI ======================
root = tk.Tk()
root.title("Tools Box")
center_window(root, 1100, 560)
root.resizable(False, False)
root.config(bg="#2c1a47")
root.iconbitmap('icon.ico')

frame_main = tk.Frame(root, bg="#2c1a47")
frame_main.pack(fill=tk.BOTH, expand=True)

# ------------------- Ліва панель профілів -------------------
frame_main = tk.Frame(root, bg="#2c1a47")
frame_main.pack(fill=tk.BOTH, expand=True)

# --- Ліва панель профілів ---
frame_profiles = tk.Frame(frame_main, bg="#2c1a47")
frame_profiles.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=10)
label_profiles = tk.Label(frame_profiles, text="Профілі", font=("Arial", 11, "bold"), bg="#2c1a47", fg="#cda4ff")
label_profiles.pack(pady=(2,8))
profile_buttons = []
for i in range(NUM_PROFILES):
    btn = tk.Button(frame_profiles, text=str(i+1), width=4, height=2,
                    command=lambda i=i: on_profile_button(i),
                    bg="#8247a8", fg="white", font=("Arial", 10, "bold"))
    btn.pack(pady=4)
    profile_buttons.append(btn)
update_profile_buttons()

# ------------------- Ліва колонка: Пошук -------------------
frame_left = tk.Frame(frame_main, bg="#2c1a47")
frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
# Labels and listbox
label_search = tk.Label(frame_left, text="Пошук файлів", font=("Arial", 12), bg="#2c1a47", fg="#cda4ff")
label_search.pack(pady=5)
label_found = tk.Label(frame_left, text="Список знайдених файлів", bg="#2c1a47", fg="#cda4ff")
label_found.pack(pady=5)
listbox_main = tk.Listbox(frame_left, width=40, height=20, bg="#3a1f5c", fg="white",
                          selectbackground="#6a0dad", selectmode=tk.EXTENDED)
listbox_main.pack(pady=5)
listbox_main.bind("<Double-1>", on_item_double_click)
frame_entry = tk.Frame(frame_left, bg="#2c1a47")
frame_entry.pack(pady=5)
path_entry = tk.Entry(frame_entry, width=25, bg="#3a1f5c", fg="white", insertbackground="white")
path_entry.pack(side=tk.LEFT, padx=5)
btn_open_entry = tk.Button(frame_entry, text="Відкрити шлях", command=open_path_from_entry,
                           bg="#6a0dad", fg="white")
btn_open_entry.pack(side=tk.LEFT)
frame_buttons = tk.Frame(frame_left, bg="#2c1a47")
frame_buttons.pack(pady=5)
btn_search = tk.Button(frame_buttons, text="Пошук", width=15, command=open_search_window,
                       bg="#6a0dad", fg="white")
btn_search.pack(side=tk.LEFT, padx=5)
btn_back = tk.Button(frame_buttons, text="Назад пошуку", width=15, command=go_back_folder,
                     bg="#6a0dad", fg="white")
btn_back.pack(side=tk.LEFT, padx=5)
btn_copy = tk.Button(frame_left, text="Копіювати вибраний файл(и)", width=40, command=copy_file_from_list,
                     bg="#6a0dad", fg="white")
btn_copy.pack(pady=5)
path_label = tk.Label(frame_left, text="Папка не вибрана", fg="#cda4ff", wraplength=250, bg="#2c1a47")
path_label.pack(pady=5)

# ------------------- Права колонка: Вставка -------------------
frame_right = tk.Frame(frame_main, bg="#2c1a47")
frame_right.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
label_insert = tk.Label(frame_right, text="Вставка файлів", font=("Arial", 12), bg="#2c1a47", fg="#cda4ff")
label_insert.pack(pady=5)
label_dest = tk.Label(frame_right, text="Список куди вставити (тільки папки)", bg="#2c1a47", fg="#cda4ff")
label_dest.pack(pady=5)
listbox_dest = tk.Listbox(frame_right, width=40, height=20, bg="#3a1f5c", fg="white", selectbackground="#6a0dad")
listbox_dest.pack(pady=5)
listbox_dest.bind("<Double-1>", on_dest_double_click)
# Поле шляху та кнопки під списком
frame_dest_entry = tk.Frame(frame_right, bg="#2c1a47")
frame_dest_entry.pack(pady=5)
dest_entry = tk.Entry(frame_dest_entry, width=25, bg="#3a1f5c", fg="white", insertbackground="white")
dest_entry.pack(side=tk.LEFT, padx=5)
btn_refresh_dest = tk.Button(frame_dest_entry, text="Оновити шлях", command=refresh_dest_path,
                             bg="#6a0dad", fg="white")
btn_refresh_dest.pack(side=tk.LEFT, padx=5)
frame_dest_buttons = tk.Frame(frame_right, bg="#2c1a47")
frame_dest_buttons.pack(pady=5)
btn_select_dest = tk.Button(frame_dest_buttons, text="Пошук папки для вставки", width=25,
                            command=select_destination_folder, bg="#6a0dad", fg="white")
btn_select_dest.pack(side=tk.LEFT, padx=5)
btn_dest_back = tk.Button(frame_dest_buttons, text="Назад вставки", width=15, command=dest_go_back,
                          bg="#6a0dad", fg="white")
btn_dest_back.pack(side=tk.LEFT, padx=5)
btn_run = tk.Button(frame_right, text="Запуск операції", width=40, command=run_operation,
                    bg="#6a0dad", fg="white")
btn_run.pack(pady=5)

# ------------------- Центр: Історія та тимчасові файли -------------------
frame_center = tk.Frame(frame_main, bg="#2c1a47")
frame_center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
label_history = tk.Label(frame_center, text="Історія операцій", bg="#2c1a47", fg="#cda4ff")
label_history.pack(pady=5)
listbox_history = tk.Listbox(frame_center, width=40, height=15, bg="#3a1f5c", fg="white", selectbackground="#6a0dad")
listbox_history.pack(pady=5)
listbox_history.bind("<Double-1>", on_history_double_click)
label_temp = tk.Label(frame_center, text="Тимчасові файли для вставки", bg="#2c1a47", fg="#cda4ff")
label_temp.pack(pady=5)
listbox_temp_files = tk.Listbox(frame_center, width=40, height=10, bg="#3a1f5c", fg="white", selectbackground="#6a0dad")
frame_temp_buttons = tk.Frame(frame_center, bg="#2c1a47")
frame_temp_buttons.pack(pady=5)
btn_clear_temp = tk.Button(frame_temp_buttons, text="Очистити список", command=clear_temp_files_list,
                           bg="#6a0dad", fg="white")
btn_clear_temp.pack(side=tk.LEFT, padx=5)
btn_remove_selected = tk.Button(frame_temp_buttons, text="Видалити виділені ❌", command=remove_selected_temp_files,
                                bg="#6a0dad", fg="white")
btn_remove_selected.pack(side=tk.LEFT, padx=5)

listbox_temp_files.bind("<Double-1>", on_temp_file_double_click)
listbox_temp_files.pack(pady=5)

btn_exit = tk.Button(frame_center, text="Вихід", width=40, command=root.quit, bg="#6a0dad", fg="white")
btn_exit.pack(pady=15)

# --- Ініціалізація ---
load_profiles()
update_profile_buttons()
refresh_history_listbox()

root.mainloop()
