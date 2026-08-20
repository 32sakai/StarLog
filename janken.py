from datetime import date
import tkinter as tk
from tkinter import messagebox

# -----------------
# テストデータ
# -----------------

schedule = {
    "月曜日": [
        {
            "subject": "数学",
            "items": ["数学の教科書"],
            "room": "2年2組",
            "homework": "問題集P12"
        },
        {
            "subject": "英語",
            "items": ["英語の教科書"],
            "room": "2年3組",
            "homework": "英単語20個"
        },
        {
            "subject": "理科",
            "items": ["理科の教科書"],
            "room": "理科室",
            "homework": "レポート作成"
        }
    ]
}

# -----------------
# 詳細表示
# -----------------

def show_detail(data):
    detail_frame = tk.Frame(root)
    detail_frame.pack(fill="both", expand=True)

    back_button = tk.Button(
        detail_frame,
        text="← 戻る",
        command=back_to_main
    )
    back_button.pack(pady=10)

    title = tk.Label(
        detail_frame,
        text=data["subject"],
        font=("Arial", 24, "bold")
    )
    title.pack(pady=10)

    room_label = tk.Label(
        detail_frame,
        text=f"教室: {data['room']}",
        font=("Arial", 16)
    )
    room_label.pack(pady=10)
    ...

room_label = tk.Label(
    detail_frame,
    text=f"教室: {data['room']}",
    font=("Arial", 16)
)

room_label.pack(pady=10)

homework_label = tk.Label(
    detail_frame,
    text=f"宿題: {data['homework']}",
    font=("Arial", 16)
)

homework_label.pack(pady=10)
title.pack(pady=20)
main_frame.pack_forget()

detail_frame.pack(
        fill="both",
        expand=True
    )

def load_day():

        for widget in lesson_frame.winfo_children():
            widget.destroy()

        day = day_var.get()
        value="月曜日"

        if day == "":
            return

        lessons = schedule[day]

        for i, lesson in enumerate(lessons):

            btn = tk.Button(
                lesson_frame,
                text=f"{i+1}時間目\n{lesson['subject']}",
                font=("Arial", 18),
                width=20,
                height=4,
                command=lambda d=lesson:
                    show_detail(d)
            )

            btn.pack(
                pady=10,
                padx=10,
                fill="x"
            )
# -----------------
# メイン画面
# -----------------

root = tk.Tk()

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

detail_frame = tk.Frame(root)

root.title("スマホ版テスト")
root.geometry("430x850")

title = tk.Label(
    detail_frame,
    text=data["subject"],
    font=("Arial", 24, "bold")
)

title.pack(pady=20)

room_label = tk.Label(
    detail_frame,
    text=f"教室: {data['room']}",
    font=("Arial", 16)
)

room_label.pack(pady=10)

homework_label = tk.Label(
    detail_frame,
    text=f"宿題: {data['homework']}",
    font=("Arial", 16)
)

homework_label.pack(pady=10)

title.pack(pady=20)

day_var = tk.StringVar()

day_menu = tk.OptionMenu(
    main_frame,
    day_var,
    "月曜日",
    command=lambda x: load_day()
)

day_menu.pack(
    pady=10
)

lesson_frame = tk.Frame(main_frame)

lesson_frame.pack(
    fill="both",
    expand=True
)

load_day()

root.mainloop()