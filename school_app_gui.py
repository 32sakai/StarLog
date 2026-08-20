import tkinter as tk
from tkinter import messagebox

subjects = {
    "国語": "国語の教科書",
    "数学": "数学の教科書",
    "英語": "英語の教科書",
    "理科": "理科の教科書",
    "社会": "地理の教科書",
    "音楽": "音楽の教科書",
    "美術": "美術の教科書",
    "保健体育": "保健体育の教科書",
    "技術・家庭": "技術・家庭の教科書"
}

schedule = []


def add_subject():
    subject = subject_var.get()

    if subject == "":
        messagebox.showwarning("注意", "教科を選んでください")
        return

    item = subjects[subject]

    schedule.append({
        "subject": subject,
        "item": item
    })

    update_list()

    messagebox.showinfo(
        "追加完了",
        f"{subject} を追加しました！\n持ち物：{item}"
    )


def update_list():
    listbox.delete(0, tk.END)

    for i, data in enumerate(schedule, start=1):
        listbox.insert(
            tk.END,
            f"{i}. {data['subject']} / 持ち物：{data['item']}"
        )


def delete_subject():
    selected = listbox.curselection()

    if not selected:
        messagebox.showwarning("注意", "削除する項目を選んでください")
        return

    index = selected[0]
    removed = schedule.pop(index)

    update_list()

    messagebox.showinfo(
        "削除完了",
        f"{removed['subject']} を削除しました！"
    )


root = tk.Tk()
root.title("中学校の持ち物管理アプリ")
root.geometry("500x500")


title_label = tk.Label(
    root,
    text="明日の授業＆持ち物管理",
    font=("Arial", 16)
)
title_label.pack(pady=10)


subject_var = tk.StringVar()

subject_menu = tk.OptionMenu(
    root,
    subject_var,
    *subjects.keys()
)
subject_menu.pack(pady=10)


add_button = tk.Button(
    root,
    text="授業を追加",
    command=add_subject
)
add_button.pack(pady=5)


listbox = tk.Listbox(
    root,
    width=50,
    height=15
)
listbox.pack(pady=10)


delete_button = tk.Button(
    root,
    text="選んだ授業を削除",
    command=delete_subject
)
delete_button.pack(pady=5)


root.mainloop()