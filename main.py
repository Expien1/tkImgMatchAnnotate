# -*- coding:utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog

from CustomWidgets import Painter, StatusBar


class UI:
    """GUI界面布局实现和主框架"""
    def __init__(self, root):
        # 设置窗口
        self.root = root
        self.root.title("YOLO Image Annotation Tool")
        self.root.geometry(str(770) + "x" + str(500))
        self.root.minsize(600, 400)

        self.init_controls()
        self.init_layout()

        # 保存图片文件夹路径
        self.folder_path = None

        # 自动切换标志
        self.auto_switch_flag = False
        # 记录开始自动切换的位置,用于停止自动切换
        self.auto_switch_start_index = 0

    def init_controls(self):
        """创建控件"""
        # 创建状态栏控件
        self.status_bar = StatusBar(self.root, text="打开图片文件夹,开始标注. "
                                                    "提示:数字按键可以切换标注类别,靠近框中心鼠标右键可删除")
        # 创建自定义的画布控件,用来显示和处理图片
        self.canvas = Painter(self.root, self.status_bar)
        # 创建文件管理按钮控件
        self.open_btn = tk.Button(self.root, text="打开文件夹(e)", command=self.open_folder)
        self.del_btn = tk.Button(self.root, text="删除该图片(q)", command=self.del_img)
        self.prev_btn = tk.Button(self.root, text="上一张(s)", command=self.prev_img)
        self.next_btn = tk.Button(self.root, text="下一张(d)", command=self.next_img)
        # 创建辅助标注按钮控件
        self.setting_btn = tk.Button(self.root, text="辅助标注设置", command=self.show_setting)
        self.yolo_btn = tk.Button(self.root, text="加载YOLO模型", command=self.load_yolo)
        self.auto_btn = tk.Button(self.root, text="开启自动切换", command=self.auto_switch)
        # 创建标签管理控件
        self.classes = ['default']  # 默认类别列表
        self.label_var = tk.StringVar(value=self.classes[0])  # 默认选中第一个类别
        self.label_combo = ttk.Combobox(root, textvariable=self.label_var, values=self.classes,
                                        state='readonly', justify='center',
                                        postcommand=self.refresh_classes)
        # self.label_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_classes())
        # 创建辅助标注模式符号框
        self.mode_var = tk.StringVar(value='手动标注')  # 默认使用'手动标注'
        self.mode_combo = ttk.Combobox(self.root, textvariable=self.mode_var,
                                       values=['手动标注', '视觉辅助标注', 'yolo辅助标注'],
                                       state='readonly', justify='center',
                                       postcommand=self.canvas.init_template_match)
        self.mode_combo.bind('<<ComboboxSelected>>', self.change_mode)

    def init_layout(self):
        """初始化布局"""
        # 定义布局管理器
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_rowconfigure(4, weight=1)
        self.root.grid_rowconfigure(5, weight=1)
        self.root.grid_rowconfigure(6, weight=1)
        self.root.grid_rowconfigure(7, weight=1)
        self.root.grid_rowconfigure(8, weight=1)
        self.root.grid_rowconfigure(9, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)

        # 设置控件布局
        self.canvas.grid(row=0, column=0, rowspan=9, padx=5, pady=5, sticky="nsew")
        self.status_bar.grid(row=9, column=0, columnspan=2, sticky="nsew")
        self.open_btn.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.del_btn.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.prev_btn.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        self.next_btn.grid(row=3, column=1, padx=5, pady=5, sticky="nsew")
        self.setting_btn.grid(row=6, column=1, padx=5, pady=5, sticky="nsew")
        self.yolo_btn.grid(row=7, column=1, padx=5, pady=5, sticky="nsew")
        self.auto_btn.grid(row=8, column=1, padx=5, pady=5, sticky="nsew")
        self.label_combo.grid(row=4, column=1, padx=5, pady=5, sticky="nsew")
        self.mode_combo.grid(row=5, column=1, padx=5, pady=5, sticky="nsew")

    def refresh_classes(self):
        """读取可标注类别,并创建复合框"""
        # 读取同级文件夹下classes.txt类别文件
        classes_path = os.path.abspath('classes.txt')
        try:
            with open(classes_path, 'r') as f:
                # 按行读取类别,并保存至列表里,strip用来移除每行末尾的换行符
                self.classes = [line.strip() for line in f]
            self.label_combo['values'] = self.classes  # 更新类别列表显示
            self.label_var.set(self.classes[0])  # 更新默认选中类别
            self.canvas.classes = self.classes  # 同步画布的类别列表
        except FileNotFoundError:
            # 对于文件不存在的情况,在状态栏和日志中返回警告
            print(f"Error: {classes_path} was not found.")
            self.status_bar.txshow(f"类别定义文件不存在!请创建类别定义文件{classes_path}", 3)
            self.classes = ['default']
        except IOError as e:
            # 对于其他I/O错误,在状态栏和日志中返回警告
            print(f"Error: {classes_path} could not be read. {e}")
            self.status_bar.txshow(f"类别文件读取错误!{classes_path}", 3)
            self.classes = ['default']
        except Exception as e:
            # 捕获其他所有异常,在状态栏和日志中返回警告
            print(f"Unexpected error occurred: {e}")
            self.status_bar.txshow(f"类别文件读取异常!{classes_path}", 3)
            self.classes = ['default']

    def open_folder(self):
        """打开文件夹按钮回调函数,弹出文件夹选择对话框并打开文件夹里的图片"""
        # 选择文件夹并加载图片
        self.folder_path = filedialog.askdirectory()  # 弹出文件夹选择对话框
        # 如果用户没有选择文件夹,则退出函数
        if self.folder_path == '':
            return
        # 读取类别列表,注意要先加载类别列表,否则无法读取新标签
        self.refresh_classes()
        # 更新画布里的类别颜色列表,每次读取到新的类别列表后,颜色列表也要更新
        self.canvas.update_classes_colors()
        # 加载图片路径到自定义画布对象,并显示图片
        self.canvas.load_imgs(self.folder_path)
        # 加载自动匹配模板
        self.canvas.init_template_match()

    def del_img(self):
        """删除图片按钮回调函数"""
        self.canvas.del_img()
        # 获取当前模式
        mode = self.mode_var.get()
        if mode == '手动标注':
            pass
        elif mode == '视觉辅助标注':
            self.canvas.add_next_template()  # 将上一张图片的模板匹配结果进行加载
            self.root.after(100, self.canvas.match_and_draw)  # 半秒后开始进行模板匹配
        elif mode == 'YOLO标注':
            pass
        # 检测是否需要自动切换
        if self.auto_switch_flag:
            if self.auto_switch_start_index != self.canvas.img_processor.get_img_index():
                # 延迟1秒后再次执行切换下一张图片
                self.root.after(3000, self.next_img)
            else:  # 回到开始位置,就关闭自动切换
                self.auto_switch_flag = False  # 关闭自动切换
                self.auto_btn.config(text="开启自动切换")

    def next_img(self):
        """下一张图片按钮回调函数"""
        self.canvas.next_img()
        # 获取当前模式
        mode = self.mode_var.get()
        if mode == '手动标注':
            pass
        elif mode == '视觉辅助标注':
            if not self.auto_switch_flag:
                self.canvas.add_next_template()  # 将上一张图片的模板匹配结果进行加载
            self.root.after(100, self.canvas.match_and_draw)  # 半秒后开始进行模板匹配
        elif mode == 'YOLO标注':
            pass
        # 检测是否需要自动切换
        if self.auto_switch_flag:
            if self.auto_switch_start_index != self.canvas.img_processor.get_img_index():
                print("自动切换下一张图片")
                # 延迟1秒后再次执行切换下一张图片
                self.root.after(3000, self.next_img)
            else:  # 回到开始位置,就关闭自动切换
                self.auto_switch_flag = False  # 关闭自动切换
                self.auto_btn.config(text="开启自动切换")

    def prev_img(self):
        """上一张图片按钮回调函数"""
        self.canvas.prev_img()
        # 获取当前模式
        mode = self.mode_var.get()
        if mode == '手动标注':
            pass
        elif mode == '视觉辅助标注':
            self.canvas.add_next_template()  # 将下一张图片的模板匹配结果进行加载
            self.root.after(100, self.canvas.match_and_draw)  # 半秒后开始进行模板匹配
        elif mode == 'YOLO标注':
            pass
        # 检测是否需要自动切换
        if self.auto_switch_flag:
            if self.auto_switch_start_index != self.canvas.img_processor.get_img_index():
                # 延迟1秒后再次执行切换下一张图片
                self.root.after(3000, self.next_img)
            else:  # 回到开始位置,就关闭自动切换
                self.auto_switch_flag = False  # 关闭自动切换
                self.auto_switch_start_index = 0  # 重置自动切换起始索引
                self.auto_btn.config(text="开启自动切换")

    def change_mode(self, event):
        """切换标注模式按钮回调函数"""
        # 获取当前模式
        mode = self.mode_var.get()
        if mode == '手动标注':
            self.status_bar.txshow("打开图片文件夹,开始标注. 提示:数字按键可以切换标注类别,靠近框中心鼠标右键可删除")
        elif mode == '视觉辅助标注':
            self.status_bar.txshow("已开启视觉辅助标注,点击下一张会自动匹配,键盘切换不会匹配,匹配错误较大的删除后可以提示匹配效果")
            # 初始化模板匹配,加载已有的模板
            self.canvas.init_template_match()
        elif mode == 'YOLO标注':
            self.status_bar.txshow("暂时没有该功能")

    def show_setting(self):
        """显示辅助标注设置窗口按钮回调函数"""
        self.canvas.create_setting_popup()

    def load_yolo(self):
        """加载YOLO模型按钮回调函数"""
        pass

    def auto_switch(self):
        """自动切换按钮回调函数"""
        if self.auto_switch_flag:  # 已开启自动切换
            self.auto_switch_flag = False  # 关闭自动切换
            self.auto_switch_start_index = 0  # 重置自动切换起始索引
            self.auto_btn.config(text='开启自动切换')
            # 重新开启键盘按键
            self.open_btn.config(state=tk.NORMAL)
            self.prev_btn.config(state=tk.NORMAL)
            self.next_btn.config(state=tk.NORMAL)
            self.del_btn.config(state=tk.NORMAL)
            self.mode_combo.config(state=tk.NORMAL)
            self.root.bind("<Key>", self.key_press)  # 键盘按键
        else:  # 当前在关闭自动切换状态
            if messagebox.askyesno("确认开启自动切换", "确定要开启自动切换吗?\n"
                                                       "每次切换到下一张图片后,会自动切换到下一张图片,"
                                                       "直到回到开始位置\n"
                                                       "提示:如果开启了辅助标注模式,则每次切换到下一张图片后,"
                                                       "都会进行标注,无法保证标注的准确性") \
                    and self.canvas.image:  # 确保当前有图片
                self.auto_switch_flag = True  # 开启自动切换
                # 获取当前图片索引
                self.auto_switch_start_index = self.canvas.img_processor.get_img_index()
                self.auto_btn.config(text='关闭自动切换')
                self.next_img()  # 切换到下一张图片,然后开始自动切换
                # 禁用所有按钮,解绑键盘按键回调函数
                self.open_btn.config(state=tk.DISABLED)
                self.prev_btn.config(state=tk.DISABLED)
                self.next_btn.config(state=tk.DISABLED)
                self.del_btn.config(state=tk.DISABLED)
                self.mode_combo.config(state=tk.DISABLED)
                self.root.unbind('<Key>')

    def key_press(self, event):
        """键盘按键回调函数"""
        if event.keysym == 'e':  # 打开文件夹
            self.open_folder()
        if event.keysym == 'd':  # 下一张图片
            self.canvas.next_img()
        if event.keysym == 's':  # 上一张图片
            self.canvas.prev_img()
        if event.keysym == 'q':  # 删除图片
            self.canvas.del_img()

        if event.keysym.isdigit():  # 数字按键
            # 数字按键设置类别
            classes_index = int(event.keysym)
            if 0 <= (classes_index-1) < len(self.classes):
                self.label_var.set(self.classes[classes_index-1])

    def mouse1_click(self, event):
        """鼠标左键点击回调函数"""
        self.canvas.adjust_rect(event)

    def mouse1_move(self, event):
        """鼠标左键拖动回调函数"""
        self.canvas.draw_rect(event)
        label_id = self.classes.index(self.label_var.get())
        self.canvas.draw_crossline(event, label_id)

    def mouse1_up(self, event):
        """鼠标左键松开回调函数"""
        label_id = self.classes.index(self.label_var.get())
        self.canvas.save_rect(event, label_id)

    def mouse3_click(self, event):
        """鼠标右键点击回调函数"""
        self.canvas.choose_del_rect(event)

    def mouse_move(self, event):
        """鼠标移动回调函数"""
        self.canvas.check_leave_rect(event)

        label_id = self.classes.index(self.label_var.get())
        self.canvas.draw_crossline(event, label_id)

    def leave_canvas(self, event):
        """鼠标离开画布回调函数"""
        self.canvas.hide_crossline()

    def configure(self, event):
        """画布设置改变回调函数"""
        self.canvas.resize_img(event)
        self.canvas.resize_rect()

    def run(self):
        """事件处理和循环"""
        # 绑定画布鼠标事件
        self.canvas.bind("<Button-1>", self.mouse1_click)  # 鼠标左键点击
        self.canvas.bind("<ButtonRelease-1>", self.mouse1_up)  # 鼠标左键松开
        self.canvas.bind("<B1-Motion>", self.mouse1_move)  # 鼠标左键拖动
        self.canvas.bind("<Motion>", self.mouse_move)  # 鼠标移动
        self.canvas.bind("<Button-3>", self.mouse3_click)  # 鼠标右键点击
        self.canvas.bind("<Leave>", self.leave_canvas)  # 鼠标离开画布
        self.canvas.bind("<Configure>", self.configure)  # 画布设置改变
        self.root.bind("<Key>", self.key_press)  # 键盘按键
        # 运行主循环
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = UI(root)
    app.run()
