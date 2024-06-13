# -*- coding:utf-8 -*-

import os
import time
from itertools import cycle
import tkinter as tk
from tkinter import messagebox, ttk

from ImageMatcher import TemplateManager
from ImageProcessor import ImageProcessor
from LabelProcessor import LabelProcessor


class StatusBar:
    """状态栏类"""

    def __init__(self, root, text=''):
        self.root = root  # 根窗口
        self.default_text = text
        self.str_var = tk.StringVar(value=text)  # 状态栏文本变量
        self.status_bar = tk.Label(self.root, textvariable=self.str_var, font=("Arial", 10))

    def grid(self, **kwargs):
        """将状态栏显示至窗口"""
        self.status_bar.grid(**kwargs)

    def txshow(self, text, second=0):
        """显示状态栏文本"""
        if second:
            self.status_bar.after(second * 1000, self.txshow, self.default_text)
        else:
            self.default_text = text
        self.str_var.set(text)


class Popup(tk.Toplevel):
    """控制弹窗类"""

    def __init__(self, root, title='popup',
                 min_width=0, min_height=0,
                 max_width=0, max_height=0,
                 hide_border=True, close_func=None):
        super().__init__(root)  # 继承Toplevel
        # 注意:如果显示边框,用户使用边框删掉弹窗就相当于使用self.destroy()销毁弹窗对象了
        self.wm_overrideredirect(hide_border)  # 隐藏窗口边框
        # 添加弹窗的widget,使用字典来存储控件,方便后续操作
        self.widgets = dict()  # 外部直接调用添加组件self.widgets['label'] = tk.Label(self, text="test")

        # 添加标题
        self.title(title)

        if min_width > 0 and min_height > 0 and max_width > 0 and max_height > 0:
            # 限制Toplevel窗口的最小尺寸
            self.minsize(width=min_width, height=min_height)
            # 限制Toplevel窗口的最大尺寸
            self.maxsize(width=max_width, height=max_height)

        # 添加关闭事件,即在点击弹窗右上角关闭按钮时触发close_func函数
        self.protocol("WM_DELETE_WINDOW", close_func)

        # 隐藏窗口,防止用户看到空白窗口
        self.withdraw()

    def pack_widgets(self, **kwargs):
        """使用pack布局显示所有控件"""
        for widget in self.widgets.values():
            widget.pack(**kwargs)

    def hide(self):
        """隐藏弹窗"""
        self.withdraw()

    def show(self):
        """显示弹窗"""
        self.deiconify()

    def move_to(self, x_root, y_root):
        """移动弹窗到指定位置"""
        # 注意:x_root和y_root是相对屏幕左上角的位置
        self.geometry(f'+{x_root}+{y_root}')

    def widget_command(self, widget_name, func, *args, **kwarg):
        """帮指定控件绑定新的回调函数"""
        self.widgets[widget_name].config(command=lambda: func(*args, **kwarg))

    def widget_bind(self, widget_name, event, func, *args, **kwarg):
        """帮指定控件绑定事件"""
        self.widgets[widget_name].bind(event, func, *args, **kwarg)

    def destroy_all(self):
        """销毁所有控件"""
        for widget in self.widgets.values():
            widget.destroy()
        self.destroy()  # 销毁弹窗对象


class Painter(tk.Canvas):
    """自定义画布控件,用来显示标注效果和图像"""

    def __init__(self, root, status_bar):
        super().__init__(root)
        # 接收状态栏控件,用于显示提示信息
        self.status_bar = status_bar
        # 创建图像处理对象
        self.img_processor = ImageProcessor()
        # 创建当前画布对图像的引用,防止在垃圾回收时意外删除图像数据
        self.image = None
        # 记录当前图片的id号
        self.image_id = None

        # 创建标签处理对象,用于读取和保存标签文件
        self.label_processor = LabelProcessor()

        # 创建类别列表
        self.classes = ['default']
        # 创建类别文本对象字典
        self.text_dict = dict()  # 键为矩形框id,值为(类别文本id,文本背景id)
        # 定义类别对应矩形框颜色,不同类别对应不同的颜色
        self.bg_colors = cycle(["Crimson", "Sienna", "DarkBlue", "DarkGreen", "Chocolate", "Purple",
                                "Gray", "Indigo", "Brown", "Maroon", "SlateGray", "OliveDrab",
                                "Navy", "SaddleBrown", "DarkOrange", "Firebrick", "BlueViolet",
                                "Magenta", "Teal"])
        self.classes_colors = dict()
        self.update_classes_colors()

        # 记录状态颜色
        self.DRAWING_RECT_COLOR = "Red"
        self.DELETE_RECT_COLOR = "DarkGray"
        self.TEXT_COLOR = "White"

        # 定义矩形框线条粗细
        self.DRAWING_RECT_WIDTH = 3
        self.FINISH_RECT_WIDTH = 5

        # 标记是否正在绘制矩形框
        self.drawing_rect = False
        # 记录当前正在绘制的矩形框id号
        self.drawing_rect_id = None
        # 记录当前正在绘制的矩形框的坐标,用于draw_rec和save_rect之间传参
        self.x_start, self.y_start = 0, 0  # 起点坐标,固定轴
        self.x_end, self.y_end = 0, 0  # 终点坐标,可变轴
        # 记录当前可调整的矩形框id号
        self.adjusting_rect_id = None
        # 记录正在调整的矩形框的坐标,用于adjust_rect和draw_rect和save_rect之间传参
        self.fixed_x, self.fixed_y = None, None  # 初始化固定轴返回值
        self.variable_x, self.variable_y = None, None  # 初始化移动轴返回值,其中移动轴设为None

        # 创建活跃状态矩形框记录列表(活跃指的是矩形框处于准备被选中状态)
        self.active_rect_ls = []
        self.chosen_rect_id = None  # 记录当前选中的矩形框id号
        # 创建删除矩形框和标签弹窗,只显示一个删除键,并且重复使用
        self.del_rect_popup = Popup(root, hide_border=True)
        # 添加删除按钮,现在暂时不用绑定回调函数,该回调函数参数是rect_id,会根据选中的矩形框改变
        self.del_rect_popup.widgets['del_btn'] = tk.Button(self.del_rect_popup, text="删 除")
        self.del_rect_popup.pack_widgets()  # 显示删除按钮

        # 创建十字架辅助线画布对象,使用4根线构成,空出鼠标位置,鼠标位置需要用于检测矩形框
        self.COSS_LINE_WIDTH = 2  # 设定十字架辅助线粗细常量
        self.COSS_LINE_DISTANCE = 25  # 设定十字架辅助线离鼠标的距离常量
        self.north_line_id, self.south_line_id = None, None  # 使用上北下南左西右东来区分
        self.west_line_id, self.east_line_id = None, None

        # 创建自动模板匹配对象
        self.template_manager = TemplateManager(self.img_processor, self.label_processor, self.status_bar)
        # 创建设置弹窗
        self.setting_popup = None

    def update_classes_colors(self):
        """更新类别颜色列表"""
        # 更新类别对应的颜色
        for i, cls in enumerate(self.classes):
            self.classes_colors[i] = next(self.bg_colors)

    def update_all(self):
        """更新画布中全部画布对象,适用于切换不同图片时对所有对象进行刷新的需求"""
        # 注意:该方法会删除全部旧的画布对象,然后生成新的画布对象
        self.delete('all')  # 删除全部旧的画布对象
        if self.image:  # 判断当前需要显示的图像是否存在
            # 更新新的图片画布对象
            # 调用ImageProcessor图像处理类里的resize_img方法获取当前图像大小
            self.image = self.img_processor.resize_img(self.winfo_width(), self.winfo_height())
            self.image_id = self.create_image(0, 0, anchor='nw', image=self.image)  # 新的画布对象
            self.lower(self.image_id)  # 将图片放置在画布最底层
            # 更新和同步类别标签文件路径
            self.label_processor.update_label_file_path(self.img_processor.get_img_path())
            # 更新矩形框画布对象
            self.label_processor.clear_rect_dict()  # 清空之前保存的矩形框
            self.draw_saved_rect()  # 绘制并保存该图片对应标签文件里已保存的矩形框
            self.active_rect_ls.clear()  # 清空活跃状态矩形框记录列表
            # 重置十字架辅助线画布对象
            self.north_line_id, self.south_line_id = None, None
            self.west_line_id, self.east_line_id = None, None
        # else:  # 如果不存在图像,则显示提示信息

    """处理图片相关方法"""

    def update_img(self):
        """只更新画布中显示的图片和其画布对象,适用于在同一个图片进行刷新的需求"""
        # 注意:该方法会删除旧的图片画布对象,然后生成新的图片画布对象
        self.delete(self.image_id)  # 每次更新新的图片时,先删除原来的图片的画布对象
        if self.image:  # 判断当前需要显示的图像是否存在
            # 调用ImageProcessor图像处理类里的resize_img方法获取当前图像大小
            self.image = self.img_processor.resize_img(self.winfo_width(), self.winfo_height())
            self.image_id = self.create_image(0, 0, anchor='nw', image=self.image)  # 新的画布对象
            self.lower(self.image_id)  # 将图片放置在画布最底层

    def load_imgs(self, folder_path):
        """加载图片路径,并显示第一张图片"""
        try:  # 检测图片路径是否加载成功
            if self.img_processor.load_img_paths(folder_path):  # 将所有图片路径加载到图像处理对象中
                self.status_bar.txshow(f"成功加载文件夹中的图片{folder_path}", 3)
            else:
                print(f"Error: {folder_path} do not have images.")
                self.status_bar.txshow(f"文件夹中没有找到图片!文件夹路径{folder_path}", 3)
                return  # 退出函数,停止显示图片
        # 加载图片失败,不继续显示图片
        except Exception as e:
            print(f"Error: {folder_path} could not be read. {e}")
            self.status_bar.txshow(f"文件夹读取错误!文件夹路径{folder_path}", 3)
            return  # 退出函数,停止显示图片
        # 获取第一张图片对象
        self.image = self.img_processor.get_new_img()
        # 更新并显示当前图片对象
        self.update_all()

    def resize_img(self, event):
        """窗口大小变化时调整图片大小"""
        # event.width和event.height为窗口变化后的画布的宽高
        if self.image:  # 判断是否存在图像
            # 调用ImageProcessor图像处理类里的resize_img方法更新图像大小
            self.image = self.img_processor.resize_img(event.width, event.height)
            # 显示更新大小后的图片
            self.update_img()  # 要改变图片尺寸,需要创建新的图片对象

    def del_img(self):
        """删除当前图片,切换并显示下一张图片"""
        if self.image:  # 存在可显示的图片,即文件夹非空
            # 获取当前图片路径,用于删除源文件
            img_path = self.img_processor.get_img_path()
            # 弹出确认删除对话框
            if messagebox.askyesno("确认删除", "确定要删除这张图片吗? \n"
                                               f"删除路径:{self.img_processor.get_img_path()}"):
                try:  # 删除图片所在的原文件
                    os.remove(img_path)
                    # 删除图片处理对象里的图片对象和引用
                    self.image = self.img_processor.del_img()  # 删除后会返回下一张图片对象
                    self.status_bar.txshow(f"成功删除图片{img_path}", 3)
                except FileNotFoundError:
                    print(f"Error: {img_path} was not found.")
                    self.status_bar.txshow(f"你正在删除不存在文件!{img_path}", 3)
                except PermissionError:
                    print(f"Error: {img_path} could not be deleted. Permission denied.")
                    self.status_bar.txshow(f"该图片文件被占用!{img_path}", 3)
                except Exception as e:
                    print(f"Error: {img_path} could not be deleted. {e}")
                    self.status_bar.txshow(f"未知异常,无法删除该图片!{img_path}", 3)
                # 获取图片对应的标签文件路径
                label_path = self.label_processor.update_label_file_path(img_path)
                # 判断标签文件是否存在
                if os.path.exists(label_path):
                    try:  # 删除图片对应的标签文件
                        os.remove(label_path)
                    except PermissionError:
                        print(f"Error: {label_path} could not be deleted. Permission denied.")
                        # self.status_label.config(text=f"警告:图片文件被占用!文件路径{label_path}")
                    except Exception as e:
                        print(f"Error: {label_path} could not be deleted. {e}")
                        # self.status_label.config(text=f"警告:图片删除异常!文件路径{label_path}")
                # 更新画布显示
                self.update_all()
        else:  # 不存在可显示的图片
            print(f"Error: folder has no images.")
            self.status_bar.txshow(f"当前文件夹中没有图片!请打开文件夹,开始标注", 3)

    def prev_img(self):
        """切换上一张图片,图片会循环切换"""
        # 显示提示信息
        if self.image:  # 存在可显示的图片,即文件夹非空
            self.image = self.img_processor.get_prev_img()  # 获取上一张图片对象
            self.update_all()  # 更新画布显示
            self.status_bar.txshow(f"成功切换到上一张图片{self.img_processor.get_img_path()}", 3)
        else:  # 不存在可显示的图片
            print(f"Error: folder has no images.")
            self.status_bar.txshow(f"当前文件夹中没有图片!请打开文件夹,开始标注", 3)

    def next_img(self):
        """切换下一张图片,图片会循环切换"""
        if self.image:  # 存在可显示的图片,即文件夹非空
            self.image = self.img_processor.get_next_img()  # 获取到下一张图片
            self.update_all()  # 更新画布显示
            self.status_bar.txshow(f"成功切换到下一张图片{self.img_processor.get_img_path()}", 3)
        else:  # 不存在可显示的图片
            print(f"Error: folder has no images.")
            self.status_bar.txshow(f"当前文件夹中没有图片!请打开文件夹,开始标注", 3)

    """处理矩形框和标签相关方法"""

    def adjust_rect(self, event):
        """调整矩形框大小"""
        if self.image:  # 存在可显示的图片,才能调整矩形框
            # 直接删除原来的矩形框,再重新绘制
            try:  # 如果self.adjusting_rect_id存的为None或是上一次的值或是已经删除的值,就跳过检测
                # 设置draw_rect方法参数,传入固定轴和移动轴,重新绘制矩形框
                # 检测鼠标的两个轴靠近哪两个轴,确定固定轴和移动轴
                x_mouse, y_mouse = event.x, event.y  # 鼠标点击时的轴的值
                # 获取需要调整的矩形框的6个轴的值
                img_width, img_height = self.img_processor.get_img_size()
                xs, ys, xe, ye = self.label_processor.get_rect_crood(self.adjusting_rect_id,
                                                                     img_width, img_height)
                xc, yc = self.label_processor.get_center_crood(self.adjusting_rect_id, img_width, img_height)
                # 判断鼠标x轴的位置,先判断鼠标x轴在矩形框中心轴的左侧还是右侧,然后再判断它接近该恻的哪一个轴,
                if x_mouse > xc:  # 鼠标x轴在矩形框中心轴的右侧
                    # 判断鼠标接近中心轴xc还是接近最右侧轴xe
                    if (x_mouse - xc) <= (xe - x_mouse):  # 鼠标x轴更接近中心轴xc
                        # 鼠标x轴接近中心轴xc,则x方向的两个轴都是固定轴,设为原来的x轴的值(将其中的可变轴设为固定轴)
                        self.fixed_x, self.variable_x = xs, xe
                    else:  # 鼠标x轴更接近最右侧轴xe
                        # 鼠标x轴接近最右侧轴xe,则将固定轴设为最左侧轴xs,移动轴设为最右侧轴(xe=None)
                        self.fixed_x, self.variable_x = xs, None  # 将最右侧轴设为移动轴
                else:  # 鼠标x轴在矩形框中心轴的左侧
                    # 判断鼠标接近中心轴xc还是接近最左侧轴xs
                    if (xc - x_mouse) <= (x_mouse - xs):  # 鼠标x轴更接近中心轴xc
                        # 鼠标x轴接近中心轴xc,则x方向的两个轴都是固定轴,设为原来的x轴的值(将其中的可变轴设为固定轴)
                        self.fixed_x, self.variable_x = xs, xe
                    else:  # 鼠标x轴更接近最左侧轴xs
                        # 鼠标x轴接近最左侧轴xs,则将固定轴设为最右侧轴xe,移动轴设为最左侧轴(xs=None)
                        self.fixed_x, self.variable_x = xe, None
                # 使用同样的方法判断鼠标y轴的位置
                if y_mouse > yc:  # 鼠标y轴在矩形框中心轴的下侧
                    if (y_mouse - yc) <= (ye - y_mouse):  # 鼠标y轴更接近中心轴yc
                        # 鼠标y轴接近中心轴yc,则y方向的两个轴都是固定轴,设为原来的y轴的值(将其中的可变轴设为固定轴)
                        self.fixed_y, self.variable_y = ys, ye
                    else:  # 鼠标y轴更接近最下侧轴ye
                        # 鼠标y轴接近最下侧轴ye,则将固定轴设为最上侧轴ys,移动轴设为最下侧轴(ye=None)
                        self.fixed_y, self.variable_y = ys, None
                else:  # 鼠标y轴在矩形框中心轴的上侧
                    if (yc - y_mouse) <= (y_mouse - ys):  # 鼠标y轴更接近中心轴yc
                        # 鼠标y轴接近中心轴yc,则y方向的两个轴都是固定轴,设为原来的y轴的值(将其中的可变轴设为固定轴)
                        self.fixed_y, self.variable_y = ys, ye
                    else:  # 鼠标y轴更接近最左侧轴ys
                        # 鼠标y轴接近最上侧轴ys,则将固定轴设为最下侧轴ye,移动轴设为最上侧轴(ys=None)
                        self.fixed_y, self.variable_y = ye, None
                # 调用draw_rect方法来开始绘制一个新的矩形框,不调用draw_rect方法则会直接跳过绘制
                self.draw_rect(event)
            except KeyError as e:
                # print(f"没有找到id为{e}的矩形框")
                pass  # 跳过检测

    def draw_rect(self, event):
        """鼠标左键按下时,根据所给的固定轴和移动轴开始绘制矩形框"""
        # 参数fixed和variable_x为确定固定轴和移动轴,固定轴为一个值,移动轴填None
        if self.image:
            # 获取图片大小,规定绘制矩形框范围,只能在图片里绘制矩形框
            img_width, img_height = self.img_processor.get_img_size()
            # 根据标记绘制矩形框
            if not self.drawing_rect:  # 标记为False,则开始绘制矩形框
                # fixed参数始终为固定轴,fixed为轴的值,fixed不能为None(None是指移动轴)
                if self.fixed_x is None or self.fixed_y is None:
                    # 现在不是调整状态,则以当前鼠标位置为起点开始绘制矩形框
                    self.x_start, self.y_start = event.x, event.y
                else:  # 现在是调整状态,则以固定轴为起点,同时隐藏当前正在调整的原矩形框
                    self.x_start, self.y_start = self.fixed_x, self.fixed_y
                    # 删除当前正在调整的矩形框,在删除之前设定self.xy_end绘制一个新的一样的矩形框
                    xs, ys, xe, ye = self.label_processor.get_rect_crood(self.adjusting_rect_id,
                                                                         img_width, img_height)
                    self.x_end, self.y_end = xe, ye  # 获取原矩形框的终点坐标,绘制一个和原矩形框一样的矩形框
                    self.del_rect(self.adjusting_rect_id)  # 最后删除原矩形框
                # 判断所设定的两个固定轴位置是否合法(即判断是否在图片范围内)
                if 0 <= self.x_start <= img_width and 0 <= self.y_start <= img_height:
                    # 原地绘制矩形框,为了获取当前矩形框的id号
                    self.drawing_rect_id = self.create_rectangle(self.x_start, self.y_start,
                                                                 self.x_start, self.y_start,
                                                                 outline=self.DRAWING_RECT_COLOR,
                                                                 width=self.DRAWING_RECT_WIDTH)
                    self.drawing_rect = True  # 将标志更新为True,表示正在绘制矩形框
            else:  # 标记为True,表示正在绘制矩形框的终点坐标
                # 规定矩形框的终点坐标在图片范围内,否则将终点坐标设置为图片边缘坐标
                # 检测variable_xy是否有记录值,有值代表是固定轴,为None则为移动轴,跟随鼠标移动
                if self.variable_x is None:  # 如果该轴为None,则该轴为可移动轴
                    self.x_end = min(event.x, img_width) if event.x > 0 else 0  # 跟随鼠标移动
                else:  # 该轴不为None,则该轴为固定轴
                    self.x_end = self.variable_x  # 该轴的值保持不变
                if self.variable_y is None:  # 如果该轴为None,则该轴为可移动轴,否则保持原值不动
                    self.y_end = min(event.y, img_height) if event.y > 0 else 0  # 跟随鼠标移动
                else:  # 该轴不为None,则该轴为固定轴
                    self.y_end = self.variable_y
                # 不断更新矩形框的终点坐标,直到鼠标左键释放,显示正在绘制的矩形框形状
                self.coords(self.drawing_rect_id, self.x_start, self.y_start, self.x_end, self.y_end)

    def save_rect(self, event, label_id):
        """鼠标左键释放时,结束绘制并记录矩形框的标注位置和标签类别"""
        if self.drawing_rect:  # 标记为True,表示正在绘制矩形框
            # 将标记更新为False,表示结束绘制矩形框
            self.drawing_rect = False
            # 记录所标注的矩形框的最终终点坐标
            # 获取图片大小,规定绘制矩形框范围,只能在图片里绘制矩形框
            img_width, img_height = self.img_processor.get_img_size()
            # 规定矩形框的终点坐标在图片范围内,否则将终点坐标记录为图片边缘坐标
            # 检测variable_xy是否有记录值,有值代表是固定轴,为None则为移动轴,跟随鼠标移动
            if self.variable_x is None:  # 如果该轴为None,则该轴为可移动轴
                self.x_end = min(event.x, img_width) if event.x > 0 else 0  # 跟随鼠标移动
            else:  # 该轴不为None,则该轴为固定轴
                self.x_end = self.variable_x  # 该轴的值保持不变
            if self.variable_y is None:  # 如果该轴为None,则该轴为可移动轴,否则保持原值不动
                self.y_end = min(event.y, img_height) if event.y > 0 else 0  # 跟随鼠标移动
            else:  # 该轴不为None,则该轴为固定轴
                self.y_end = self.variable_y
            # 市镇将左上角坐标作为开始坐标,右下角坐标作为终点坐标,判断并转换坐标
            if self.x_start > self.x_end:  # 如果左上角坐标大于右下角坐标,则交换坐标
                self.x_start, self.x_end = self.x_end, self.x_start
            if self.y_start > self.y_end:
                self.y_start, self.y_end = self.y_end, self.y_start
            # 检测框定范围,如果框定范围过小(小于图片长度的5%)则不保存
            min_rect_x, min_rect_y = (img_width * 0.05), (img_height * 0.05)
            # 判断矩形框是否过小,过小则不保存
            if ((self.x_end - self.x_start) > min_rect_x
                    and (self.y_end - self.y_start) > min_rect_y):
                # 更新最终的矩形框位置
                self.coords(self.drawing_rect_id, self.x_start, self.y_start, self.x_end, self.y_end)
                self.itemconfig(self.drawing_rect_id, width=self.FINISH_RECT_WIDTH,
                                outline=self.classes_colors[label_id])  # 调整成最终矩形框的样式
                # 将矩形框绑定鼠标事件
                self.tag_bind(self.drawing_rect_id, "<Enter>",
                              lambda e, r_id=self.drawing_rect_id: self.touch_rect(e, r_id))
                self.tag_bind(self.drawing_rect_id, "<Leave>",
                              lambda e, r_id=self.drawing_rect_id: self.leave_rect(e, r_id))
                # 记录当前矩形框的标注位置和标签类别
                self.label_processor.record_rect(img_width, img_height,
                                                 self.drawing_rect_id, label_id,
                                                 self.x_start, self.y_start,
                                                 self.x_end, self.y_end)
                # 绘制该矩形框的标签
                self.draw_text(self.drawing_rect_id, label_id, self.x_start, self.y_start)
                try:  # 捕获写入标签文件异常
                    # 将当前矩形框的标签信息写入yolo标签文件
                    self.label_processor.save_label_file(self.drawing_rect_id, img_width, img_height)
                except PermissionError:
                    label_file_path = self.label_processor.label_file_path
                    print(f"Error: {label_file_path} could not be written. Permission denied.")
                    self.status_bar.txshow(f"图片的标签文件被占用,无法写入!{label_file_path}", 3)
                except Exception as e:
                    label_file_path = self.label_processor.label_file_path
                    print(f"Error: {label_file_path} could not be read. {e}")
                    self.status_bar.txshow(f"未知异常,标签文件读取异常!{label_file_path}", 3)
            else:  # 框定范围过小,不保存,并删除该矩形框
                self.delete(self.drawing_rect_id)

        # 保持完毕,将记录正在调整的矩形框id标记重置
        self.adjusting_rect_id = None
        # 将调整的轴变量置为None
        self.fixed_x, self.fixed_y = None, None
        self.variable_x, self.variable_y = None, None

    def draw_saved_rect(self):
        """绘制已保存的矩形框"""
        # 获取当前图片的大小,用于转换坐标
        img_width, img_height = self.img_processor.get_img_size()
        try:  # 捕获读取标签文件失败的异常
            # 读取已保存的标签信息,并将已保存的标签信息转换为矩形框坐标
            rect_ls = self.label_processor.load_labels_to_rects(img_width, img_height)
            # 绘制所有已保存的矩形框
            for label_id, x_start, y_start, x_end, y_end in rect_ls:
                # 绘制矩形框并保存矩形框的id号
                rect_id = self.create_rectangle(x_start, y_start, x_end, y_end,
                                                outline=self.classes_colors[label_id],
                                                width=self.FINISH_RECT_WIDTH)
                # 将矩形框绑定鼠标事件
                self.tag_bind(rect_id, "<Enter>", lambda e, r_id=rect_id: self.touch_rect(e, r_id))
                self.tag_bind(rect_id, "<Leave>", lambda e, r_id=rect_id: self.leave_rect(e, r_id))
                self.label_processor.record_rect(img_width, img_height,
                                                 rect_id, label_id, x_start, y_start, x_end, y_end)
                # 绘制该矩形框的标签
                self.draw_text(rect_id, label_id, x_start, y_start)
        except FileNotFoundError:  # 读取标签文件失败
            label_file_path = self.label_processor.label_file_path
            print(f"Error: {label_file_path} was not found.")
            self.status_bar.txshow(f"没找到该图片的标签文件{label_file_path}", 3)
        except PermissionError:
            label_file_path = self.label_processor.label_file_path
            print(f"Error: {label_file_path} could not be read. Permission denied.")
            self.status_bar.txshow(f"图片的标签文件被占用,无法读取!{label_file_path}", 3)
        except Exception as e:
            label_file_path = self.label_processor.label_file_path
            print(f"Error: {label_file_path} could not be read. {e}")
            self.status_bar.txshow(f"未知异常,标签文件读取异常!{label_file_path}", 3)

    def resize_rect(self):
        """根据窗口变化大小,计算并重新绘制所有矩形框"""
        if self.image:  # 存在可显示的图片
            # 获取调整后的矩形框大小
            img_width, img_height = self.img_processor.get_img_size()
            # 获取已经保存的矩形框信息
            rect_dict = self.label_processor.get_rect_dict(img_width, img_height)
            # 重新绘制所有矩形框
            for rect_id, (label_id, x_start, y_start, x_end, y_end) in rect_dict.items():
                # 根据矩形框id重新绘制矩形框的位置
                self.coords(rect_id, x_start, y_start, x_end, y_end)
                self.move_text_to(rect_id, x_start, y_start)  # 移动矩形框的标签

    def del_rect(self, rect_id, check_template=False):
        """删除已经保存的矩形框"""
        # 检查需要删除的矩形框是否为自动生成的矩形框,来查看是否需要删除该矩形框对应的模板
        if check_template: self.check_template(rect_id)
        # 删除矩形框
        self.delete(self.text_dict[rect_id][0])  # 删除矩形框的标签文本
        self.delete(self.text_dict[rect_id][1])  # 删除矩形框的标签文本背景
        self.delete(rect_id)  # 删除矩形框
        self.text_dict.pop(rect_id)  # 删除标签文本字典里对应的矩形框
        try:
            self.active_rect_ls.remove(rect_id)  # 将被删矩形框从列表中删除
        except ValueError:  # 对于不在活跃列表中的矩形框,不进行删除,直接
            pass

        try:  # 捕获文件读写异常
            # 从标签文件中删除矩形框标签
            self.label_processor.adjust_label_file(rect_id, mode="delete")
        except PermissionError:
            label_path = self.label_processor.label_file_path
            print(f"Error: {label_path} could not be writen. Permission denied.")
            self.status_bar.txshow(f"图片的标签文件被占用,无法读取!{label_path}", 3)
        except Exception as e:
            label_path = self.label_processor.label_file_path
            print(f"Error: {label_path} could not be writen. {e}")
            self.status_bar.txshow(f"未知异常,标签文件读取异常!{label_path}", 3)
        # 标签和矩形框删除完毕,继续隐藏删除提示框
        self.del_rect_popup.hide()

    def touch_rect(self, event, rect_id):
        """鼠标触碰矩形框边界事件"""
        # 鼠标碰到矩形框边界时,记录该矩形框为可调动,改变颜色,即提示可以进行调整
        self.adjusting_rect_id = rect_id  # 记录当前触碰的矩形框id(即可调整的矩形框id)
        self.itemconfig(self.adjusting_rect_id, outline=self.DRAWING_RECT_COLOR)
        self.itemconfig(self.text_dict[self.adjusting_rect_id][1], fill=self.DRAWING_RECT_COLOR)
        # 检测并添加活跃的矩形框(活跃即处于准备被选中状态)
        if rect_id not in self.active_rect_ls:
            self.active_rect_ls.append(rect_id)  # 将被鼠标触碰到的矩形框添加到活跃列表中

    def scale_bbox(self, rect_id, scale_rate):
        """返回缩放之后的bbox边界坐标"""
        bbox = self.bbox(rect_id)  # 计算得到原来的矩形框的边界坐标
        if bbox is None:
            return None  # 矩形框不存在则返回None
        else:
            # scale_rate为缩窄范围比率
            bx_start = ((1 + scale_rate) / 2) * bbox[0] + ((1 - scale_rate) / 2) * bbox[2]
            bx_end = ((1 + scale_rate) / 2) * bbox[2] + ((1 - scale_rate) / 2) * bbox[0]
            by_start = ((1 + scale_rate) / 2) * bbox[1] + ((1 - scale_rate) / 2) * bbox[3]
            by_end = ((1 + scale_rate) / 2) * bbox[3] + ((1 - scale_rate) / 2) * bbox[1]
            # 以上公式可以展开成下面的语句(用的方法不同,上面的是化简之后的公式)
            # half_width = ((bbox[2] - bbox[0]) * 0.8) // 2  # 新框定范围的一半长度(取整)
            # half_height = ((bbox[3] - bbox[1]) * 0.8) // 2
            # bx_start = ((bbox[0] + bbox[2]) // 2) - half_width  # 在中点向两边移动一半长度
            # bx_end = ((bbox[0] + bbox[2]) // 2) + half_width
            # by_start = ((bbox[1] + bbox[3]) // 2) - half_height
            # by_end = ((bbox[1] + bbox[3]) // 2) + half_height
            return bx_start, by_start, bx_end, by_end

    def leave_rect(self, event, rect_id):
        """鼠标离开矩形框边界事件"""
        # 鼠标离开矩形框边界时,恢复颜色,不可调整矩形框大小
        label_id = self.label_processor.get_label_id(rect_id)
        self.itemconfig(rect_id, outline=self.classes_colors[label_id])
        self.itemconfig(self.text_dict[rect_id][1], fill=self.classes_colors[label_id])
        # 将记录正在调整的矩形框id标记重置
        self.adjusting_rect_id = None
        self.fixed_x, self.fixed_y = None, None  # 将调整的轴变量置为None
        self.variable_x, self.variable_y = None, None
        # 将鼠标离开至矩形框外的活跃矩形框设为不活跃(即移出活跃列表)
        for active_rect_id in self.active_rect_ls:  # 遍历活跃的矩形框列表
            bbox = self.bbox(active_rect_id)  # 获取矩形框的边界
            if bbox is None:  # 矩形框不存在
                self.active_rect_ls.remove(active_rect_id)  # 该矩形框不存在,则直接从活跃列表中移除
                # print(f"Error: {active_rect_id} does not exist.")
                continue
            if bbox[0] < event.x < bbox[2] and bbox[1] < event.y < bbox[3]:
                # 在矩形框内,则矩形框为活跃状态,不进行操作
                continue
            else:  # 在矩形框外,则矩形框为不活跃状态,移出活跃列表
                self.active_rect_ls.remove(active_rect_id)

    def check_leave_rect(self, event):
        """鼠标移动事件,检查鼠标是否移出选中的矩形框"""
        if self.chosen_rect_id is not None:  # 已选中矩形框
            # 检查鼠标当前位置是否还在矩形框内
            bbox = self.scale_bbox(self.chosen_rect_id, 0.8)
            if bbox is not None:  # 矩形框边界存在
                # 取矩形框内70%的范围内作为检测,避免与调整矩形框的操作冲突
                if not (bbox[0] < event.x < bbox[2] and bbox[1] < event.y < bbox[3]):
                    # 鼠标不在矩形框70%范围内,则移除选中的矩形框
                    # 恢复矩形框颜色,恢复标签背景颜色
                    label_id = self.label_processor.get_label_id(self.chosen_rect_id)
                    self.itemconfig(self.chosen_rect_id, outline=self.classes_colors[label_id])
                    self.itemconfig(self.text_dict[self.chosen_rect_id][1],
                                    fill=self.classes_colors[label_id])
                    # 只移除选中的矩形框即可,因为鼠标可能还在矩形框框内,可能处于准备被选中状态
                    self.chosen_rect_id = None  # 移除选中的矩形框
                    # 重新隐藏删除弹窗,并重新将回调函数设为None,保险一点
                    self.del_rect_popup.widget_command('del_btn', None)
                    self.del_rect_popup.hide()

    def choose_del_rect(self, event):
        """鼠标右键点击事件"""
        # 检查鼠标当前位置是否在矩形框内
        # 将鼠标离开至矩形框外的活跃矩形框设为不活跃(即移出活跃列表)
        for active_rect_id in self.active_rect_ls:  # 遍历活跃的矩形框列表
            bbox = self.scale_bbox(active_rect_id, 0.7)  # 获取矩形框的边界,采用0.8的缩窄比例
            if bbox is None:  # 矩形框不存在
                self.active_rect_ls.remove(active_rect_id)  # 该矩形框不存在,则直接从活跃列表中移除
                # print(f"Error: {active_rect_id} does not exist.")
                continue
            if bbox[0] < event.x < bbox[2] and bbox[1] < event.y < bbox[3]:
                # 在矩形框内,则矩形框为活跃状态,不进行操作
                continue
            else:  # 在矩形框外,则矩形框为不活跃状态,移出活跃列表
                self.active_rect_ls.remove(active_rect_id)
        # 判断当前是否存在活跃的矩形框
        if self.active_rect_ls:  # 如果移除完不在范围的矩形框后还有矩形框
            # 获取鼠标归一化后的位置
            img_width, img_height = self.img_processor.get_img_size()
            x_mouse, y_mouse = (event.x / img_width), (event.y / img_height)
            # 遍历并比较剩下的矩形框中心点位置,选取最靠近鼠标的矩形框
            closest_rect_id = self.active_rect_ls[0]  # 默认选中第一个矩形框
            for active_rect_id in self.active_rect_ls:
                # 计算矩形框中心点位置与鼠标位置的没有开根号的欧式距离
                x_close, y_close = self.label_processor.get_center_label_crood(closest_rect_id)
                x_new, y_new = self.label_processor.get_center_label_crood(active_rect_id)
                distance_close = (x_mouse - x_close) ** 2 + (y_mouse - y_close) ** 2
                distance_new = (x_mouse - x_new) ** 2 + (y_mouse - y_new) ** 2
                if distance_new > distance_close:  # 比较欧式距离,如果新矩形框距离鼠标更近,则选中新矩形框
                    closest_rect_id = active_rect_id
            # 选出最终的矩形框,改变颜色,并弹出删除按钮
            self.chosen_rect_id = closest_rect_id
            self.itemconfig(closest_rect_id, outline=self.DELETE_RECT_COLOR)
            self.itemconfig(self.text_dict[closest_rect_id][1], fill=self.DELETE_RECT_COLOR)
            # 为删除按钮绑定新的回调函数,传入需要删除的矩形框id,弹出删除按钮(即显示删除弹窗)
            self.del_rect_popup.widget_command('del_btn', self.del_rect,
                                               rect_id=closest_rect_id, check_template=True)
            self.del_rect_popup.move_to(event.x_root, event.y_root)  # 移动到鼠标位置
            self.del_rect_popup.show()

    """绘制文字相关方法"""

    def draw_text(self, rect_id, label_id=None, x_rect0=None, y_rect0=None, is_auto_rect=False):
        """绘制矩形框类别标签"""
        # 获取该矩形框的类别标签文本
        if label_id is None:
            label_id = self.label_processor.get_label_id(rect_id)
        # 获取该矩形框的类别标签文本
        label_text = self.classes[label_id]
        if is_auto_rect:
            label_text = label_text + ':auto'
        # 获取该矩形框的坐标,只需要左上角坐标
        if x_rect0 is None or y_rect0 is None:
            x_rect0, y_rect0, *_ = self.bbox(rect_id)
            x_rect0, y_rect0 = (x_rect0 + 4), (y_rect0 + 4)  # 矩形框左上角坐标加上其边框宽度
        # 绘制类别标签文本
        text_id = self.create_text(x_rect0, y_rect0, text=label_text, fill=self.TEXT_COLOR,
                                   anchor='nw', font=("Arial", 10))
        # 绘制文本背景
        color = self.classes_colors[label_id]
        x_start, y_start, x_end, y_end = self.bbox(text_id)  # 获取标签文本位置坐标
        bg_id = self.create_rectangle(x_start, y_start, x_end, y_end, fill=color, width=0)
        self.lower(bg_id, text_id)  # 将背景的显示顺序
        # 将文本背景和文本保存到字典中
        self.text_dict[rect_id] = (text_id, bg_id)
        # 将文本和文本背景也绑定到矩形框的鼠标事件里,防止文本和文本背景会阻碍调整矩形框
        self.tag_bind(text_id, "<Enter>", lambda e, r_id=rect_id: self.touch_rect(e, r_id))
        self.tag_bind(text_id, "<Leave>", lambda e, r_id=rect_id: self.leave_rect(e, r_id))
        self.tag_bind(bg_id, "<Enter>", lambda e, r_id=rect_id: self.touch_rect(e, r_id))
        self.tag_bind(bg_id, "<Leave>", lambda e, r_id=rect_id: self.leave_rect(e, r_id))

    def move_text_to(self, rect_id, x_rect0=None, y_rect0=None):
        """类别文本跟随矩形框移动"""
        # 获取该矩形框的坐标,只需要左上角坐标
        if x_rect0 is None or y_rect0 is None:
            x_rect0, y_rect0, *_ = self.bbox(rect_id)
            x_rect0, y_rect0 = (x_rect0 + 4), (y_rect0 + 4)  # 矩形框左上角坐标加上其边框宽度
        # 移动类别标签文本至矩形框左上角
        self.coords(self.text_dict[rect_id][0], x_rect0, y_rect0)
        x_start, y_start, x_end, y_end = self.bbox(self.text_dict[rect_id][0])
        self.coords(self.text_dict[rect_id][1], x_start, y_start, x_end, y_end)

    """绘制十字架线相关方法"""

    def draw_crossline(self, event, label_id):
        """在绘制矩形时,绘制十字架辅助线"""
        if self.image:  # 图片存在才绘制十字架线
            # 获取图片尺寸
            img_width, img_height = self.img_processor.get_img_size()
            # 检查鼠标是否在图片内,如果不在图片内,则不绘制十字架线
            if 0 <= event.x <= img_width and 0 <= event.y <= img_height:
                # 获取当前正在绘制的矩形框的类别颜色
                line_color = self.classes_colors[label_id]
                # 绘制的直线需要在这里绘制,并存储id,因为每次切换下一张图片都会更新所有画布对象,delete('all')
                if (self.north_line_id is None or self.south_line_id is None
                        or self.west_line_id is None or self.east_line_id is None):
                    # dash虚线参数(虚线间隔,虚线长度),简单来讲就是前大后小就疏,后大前小就密
                    self.north_line_id = self.create_line(event.x, event.y - self.COSS_LINE_DISTANCE,
                                                          event.x, 0, fill=line_color,
                                                          width=self.COSS_LINE_WIDTH, dash=(200, 200))
                    self.south_line_id = self.create_line(event.x, event.y + self.COSS_LINE_DISTANCE,
                                                          event.x, img_height, fill=line_color,
                                                          width=self.COSS_LINE_WIDTH, dash=(200, 200))
                    self.west_line_id = self.create_line(event.x - self.COSS_LINE_DISTANCE, event.y,
                                                         0, event.y, fill=line_color,
                                                         width=self.COSS_LINE_WIDTH, dash=(200, 200))
                    self.east_line_id = self.create_line(event.x + self.COSS_LINE_DISTANCE, event.y,
                                                         img_width, event.y, fill=line_color,
                                                         width=self.COSS_LINE_WIDTH, dash=(200, 200))
                else:  # 鼠标移动,则十字架线移动
                    # 将十字架线的颜色改成当前类别颜色
                    self.itemconfig(self.north_line_id, fill=line_color)
                    self.itemconfig(self.south_line_id, fill=line_color)
                    self.itemconfig(self.west_line_id, fill=line_color)
                    self.itemconfig(self.east_line_id, fill=line_color)
                    # 将十字架线移动至鼠标位置
                    x_mouse, y_mouse = event.x, event.y
                    self.coords(self.north_line_id, event.x, event.y - self.COSS_LINE_DISTANCE, event.x, 0)
                    self.coords(self.south_line_id,
                                event.x, event.y + self.COSS_LINE_DISTANCE, event.x, img_height)
                    self.coords(self.west_line_id, event.x - self.COSS_LINE_DISTANCE, event.y, 0, event.y)
                    self.coords(self.east_line_id,
                                event.x + self.COSS_LINE_DISTANCE, event.y, img_width, event.y)
                    # 将十字架线显示在最上层
                    self.tkraise(self.north_line_id)
                    self.tkraise(self.south_line_id)
                    self.tkraise(self.west_line_id)
                    self.tkraise(self.east_line_id)

    def hide_crossline(self):
        """隐藏十字架线"""
        if (self.north_line_id is not None or self.south_line_id is not None
                or self.west_line_id is not None or self.east_line_id is not None):
            # 将十字架线移动到画布最下层
            self.lower(self.north_line_id)
            self.lower(self.south_line_id)
            self.lower(self.west_line_id)
            self.lower(self.east_line_id)

    """自动模板匹配相关方法"""

    def init_template_match(self):
        """初始化自动模板匹配,加载已有模板"""
        self.template_manager.load_all_templates()

    def add_last_template(self, img_path):
        """加载上一张图片的标签作为模板"""
        img_path = self.img_processor.get_last_img_path()
        if img_path:  # 如果成功获取到上一张图片的路径就加载其模板,否则不加载
            self.template_manager.load_template(img_path)

    def add_next_template(self):
        """加载下一张图片的标签作为模板"""
        img_path = self.img_processor.get_next_img_path()
        if img_path:  # 如果成功获取到下一张图片的路径就加载其模板,否则不加载
            self.template_manager.load_template(img_path)

    def check_template(self, rect_id):
        """删除对当前照片进行匹配的模板"""
        # 检查当前矩形框是否是匹配生成的
        text_id = self.text_dict[rect_id][0]  # 获取当前矩形框的标签文本id
        # 使用该矩形框的标签文本是否含有'auto'来判断是否是自动匹配的模板
        if 'auto' in self.itemcget(text_id, 'text'):  # 如果含有'auto'则删除该模板
            label_id = self.label_processor.get_label_id(rect_id)  # 获取当前矩形框的标签id
            self.template_manager.delete_last_template(label_id)  # 删除该模板

    def match_and_draw(self):
        """开始自动匹配模板并重绘矩形框"""
        # 获取匹配结果
        rect_ls = self.template_manager.match_all_classes()
        # 遍历所有匹配结果
        for yolo_num in rect_ls:
            img_width, img_height = self.img_processor.get_img_size()  # 获取当前图像宽高
            label_id, *rect_crood = self.label_processor.yolo_num_to_rect(img_width, img_height, *yolo_num)
            # 绘制矩形框并保存矩形框的id号
            rect_id = self.create_rectangle(*rect_crood, outline=self.classes_colors[label_id],
                                            width=self.FINISH_RECT_WIDTH)
            # 将矩形框绑定鼠标事件
            self.tag_bind(rect_id, "<Enter>", lambda e, r_id=rect_id: self.touch_rect(e, r_id))
            self.tag_bind(rect_id, "<Leave>", lambda e, r_id=rect_id: self.leave_rect(e, r_id))
            self.label_processor.record_rect(img_width, img_height,
                                             rect_id, label_id, *rect_crood)
            # 绘制该矩形框的标签
            self.draw_text(rect_id, label_id, *(rect_crood[:2]), is_auto_rect=True)

    def create_setting_popup(self):
        """创建一个自动辅助匹配的设置窗口"""
        if self.setting_popup is None:  # 如果没有创建过窗口就创建
            self.setting_popup = Popup(self, title='视觉辅助设置', min_width=250, min_height=250,
                                       max_width=300, max_height=300,
                                       hide_border=False, close_func=self.close_setting_popup)
            # 设置最大模板存储数量
            self.setting_popup.widgets['num_label'] = tk.Label(self.setting_popup, text='最大模板存储数量:')
            self.num_var = tk.IntVar(value=self.template_manager.get_max_template_num())
            self.setting_popup.widgets['num_combo'] = ttk.Combobox(self.setting_popup,
                                                                   textvariable=self.num_var,
                                                                   values=list(map(str, range(1, 101))),
                                                                   state='readonly', justify='center')
            self.setting_popup.widget_bind('num_combo', '<<ComboboxSelected>>',
                                           self.set_num_combo)
            # 设置成功匹配的最小阈值
            self.setting_popup.widgets['thr_label'] = tk.Label(self.setting_popup,
                                                               text='成功匹配的最小阈值:')
            self.thr_var = tk.DoubleVar(value=self.template_manager.get_threshold())
            self.setting_popup.widgets['thr_combo'] = ttk.Combobox(self.setting_popup,
                                                                   textvariable=self.thr_var,
                                                                   values=list(
                                                                       map(lambda x: f'{(x / 100):.2f}',
                                                                           range(0, 101, 5))
                                                                   ),
                                                                   state='readonly', justify='center')
            self.setting_popup.widget_bind('thr_combo', '<<ComboboxSelected>>',
                                           self.set_thr_combo)
            # 设置是否使用高相似度匹配
            self.sim_var = tk.StringVar(value='关闭使用更高的匹配相似度')
            self.set_sim_btn_text()  # 设置相似度按钮的文本
            self.setting_popup.widgets['high_sim_btn'] = tk.Button(self.setting_popup,
                                                                   textvariable=self.sim_var,
                                                                   command=self.set_sim_btn)
            # 设置是否调整匹配结果
            self.adjust_var = tk.StringVar(value='关闭自动调整矩形框大小')
            self.set_adjust_btn_text()  # 设置调整按钮的文本
            self.setting_popup.widgets['adjust_btn'] = tk.Button(self.setting_popup,
                                                                 textvariable=self.adjust_var,
                                                                 command=self.set_adjust_btn)
            self.setting_popup.widgets['ok_btn'] = tk.Button(self.setting_popup,
                                                             text='设置完毕',
                                                             command=self.close_setting_popup)
            self.setting_popup.pack_widgets(expand=True, fill='both')  # 将窗口中的组件进行布局
            self.setting_popup.move_to(self.winfo_rootx(), self.winfo_rooty())
            self.setting_popup.show()  # 显示窗口
        else:  # 如果已经创建过窗口就重新显示窗口
            self.setting_popup.show()

    def set_num_combo(self, event):
        """设置窗口的最大模板存储数量下拉框的回调函数"""
        # 获取当前下拉框选中的值
        new_max_template_num = int(self.num_var.get())
        # 调用模板管理器中的函数来设置最大模板存储数量
        self.template_manager.set_max_template_num(new_max_template_num)

    def set_thr_combo(self, event):
        """设置窗口的成功匹配的最小阈值下拉框的回调函数"""
        # 获取当前下拉框选中的值
        new_threshold = float(self.thr_var.get())
        # 调用模板管理器中的函数来设置成功匹配的最小阈值
        self.template_manager.set_threshold(new_threshold)

    def set_sim_btn(self):
        """设置窗口的高相似度匹配按钮的回调函数"""
        if self.template_manager.get_higher_similarity():  # 当前已开启高相似度匹配
            self.template_manager.set_higher_similarity(False)  # 调成成关闭状态
        else:  # 当前未开启高相似度匹配
            self.template_manager.set_higher_similarity(True)
        self.set_sim_btn_text()  # 设置按钮的文本

    def set_sim_btn_text(self):
        """设置高相似度匹配按钮的文本"""
        # 根据当前是否使用高相似度匹配来设置按钮的文本
        if self.template_manager.get_higher_similarity():  # 当前已开启高相似度匹配
            self.sim_var.set('关闭使用更高的匹配相似度')
        else:  # 当前未开启高相似度匹配
            self.sim_var.set('开启使用更高的匹配相似度')

    def set_adjust_btn(self):
        """设置窗口的调整匹配结果按钮的回调函数"""
        if self.template_manager.get_adjust_result():  # 当前已开启调整匹配结果
            self.template_manager.set_adjust_result(False)  # 调成成关闭调整匹配结果
        else:  # 当前未开启调整匹配结果
            self.template_manager.set_adjust_result(True)
        self.set_adjust_btn_text()  # 设置按钮的文本

    def set_adjust_btn_text(self):
        """设置调整匹配结果按钮的文本"""
        # 根据当前是否调整匹配结果来设置按钮的文本
        if self.template_manager.get_adjust_result():  # 当前已开启调整匹配结果
            self.adjust_var.set('关闭自动调整矩形框大小')
        else:  # 当前未开启调整匹配结果
            self.adjust_var.set('开启自动调整矩形框大小')

    def close_setting_popup(self):
        """关闭自动辅助匹配的设置窗口的回调函数"""
        self.setting_popup.destroy_all()  # 销毁窗口
        self.setting_popup = None  # 将窗口置为None,防止重复创建
