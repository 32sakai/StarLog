import tkinter as tk
from tkinter import messagebox

subjects = {
    "国語": {
        "item": "国語の教科書",
        "room": "2年1組",
        "homework": "漢字練習",
        "test": "来週 小テスト",
        "submission": "ワーク提出"
    },
    "数学": {
        "item": "数学の教科書",
        "room": "2年2組",
        "homework": "問題集 P12",
        "test": "金曜日 単元テスト",
        "submission": "ノート提出"
    },
    "英語": {
        "item": "英語の教科書",
        "room": "2年3組",
        "homework": "英単語20個",
        "test": "月曜日 単語テスト",
        "submission": "プリント提出"
    },
    "理科": {
        "item": "理科の教科書",
        "room": "理科室",
        "homework": "実験レポート",
        "test": "木曜日 小テスト",
        "submission": "レポート提出"
    },
    "社会": {
        "item": "地理の教科書",
        "room": "2年1組",
        "homework": "地図問題",
        "test": "来週 地理テスト",
        "submission": "プリント提出"
    }
}

schedule = []


def add_subject():
    subject = subject_var.get()

    if subject == "":
        messagebox.showwarning("注意", "教科を選んでください")
        return

    schedule.append(subject)
    update_list()

    messagebox.showinfo(
        "追加完了",
        f"{subject} を追加しました！"
    )


def update_list():
    listbox.delete(0, tk.END)

    for i, subject in enumerate(schedule, start=1):
        listbox.insert(tk.END, f"{i}. {subject}")


def show_detail():
    selected = listbox.curselection()

    if not selected:
        messagebox.showwarning("注意", "授業を選んでください")
        return

    index = selected[0]
    subject = schedule[index]
    data = subjects[subject]

    detail_window = tk.Toplevel(root)
    detail_window.title(f"{subject} の詳細")
    detail_window.geometry("400x350")

    tk.Label(
        detail_window,
        text=f"【{subject}】",
        font=("Arial", 16)
    ).pack(pady=10)

    tk.Label(
        detail_window,
        text=f"持ち物：{data['item']}",
        font=("Arial", 12)
    ).pack(pady=5)

    tk.Label(
        detail_window,
        text=f"教室：{data['room']}",
        font=("Arial", 12)
    ).pack(pady=5)

    tk.Label(
        detail_window,
        text=f"宿題：{data['homework']}",
        font=("Arial", 12)
    ).pack(pady=5)

    tk.Label(
        detail_window,
        text=f"テスト予定：{data['test']}",
        font=("Arial", 12)
    ).pack(pady=5)

    tk.Label(
        detail_window,
        text=f"提出物：{data['submission']}",
        font=("Arial", 12)
    ).pack(pady=5)


def delete_subject():
    selected = listbox.curselection()

    if not selected:
        messagebox.showwarning("注意", "削除する授業を選んでください")
        return

    index = selected[0]
    removed = schedule.pop(index)

    update_list()

    messagebox.showinfo(
        "削除完了",
        f"{removed} を削除しました！"
    )


root = tk.Tk()
root.title("学校用 持ち物管理アプリ")
root.geometry("500x550")


title_label = tk.Label(
    root,
    text="授業＆詳細管理アプリ",
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
    command=add_subject,
    font=("Arial", 12),
    width=20,
    height=2
)
add_button.pack(pady=5)


listbox = tk.Listbox(
    root,
    width=40,
    height=12,
    font=("Arial", 12)
)
listbox.pack(pady=10)


detail_button = tk.Button(
    root,
    text="詳細を見る",
    command=show_detail,
    font=("Arial", 12),
    width=20,
    height=2
)
detail_button.pack(pady=5)


delete_button = tk.Button(
    root,
    text="選んだ授業を削除",
    command=delete_subject,
    font=("Arial", 12),
    width=20,
    height=2
)
delete_button.pack(pady=5)


root.mainloop()