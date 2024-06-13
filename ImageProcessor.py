# -*- coding: utf-8 -*-

import os
import glob

import numpy as np
from PIL import Image, ImageTk


class ImageProcessor:
    """图片处理类"""
    def __init__(self):
        # 定义可用的图片后缀
        self.img_suffix = ['.jpg', '.jpeg', '.png']
        # 创建图片路径列表
        self.img_paths = []
        # 定义当前图片的索引
        self.cur_img_index = 0

        # 创建当前的PIL图片对象
        self.pil_img = None
        # 创建当前的cv2图片对象
        self.cv_img = None
        # 创建当前图片的tk图片对象
        self.tk_img = None

        # 定义当前图片尺寸以及图片比例
        self.img_width = 0
        self.img_height = 0
        self.img_ratio = 0

        # 定义当前图片的矩形框列表
        self.rect_ls = []  # 矩形框列表

    def load_img_paths(self, folder_path):
        """获取文件夹下所有图片的路径列表"""
        # 遍历文件夹下所有文件使用glob函数进行匹配,然后筛选出符合要求的图片路径
        self.img_paths = [img_path.replace('\\', '/')
                          for img_path in glob.iglob(os.path.join(folder_path, '*'))
                          if os.path.splitext(img_path)[1].lower() in self.img_suffix]
        # 上面加载的路径其中有'\\'和'/'分隔符混用的情况,所以用.replace('\\', '/')来统一
        # 检查文件夹是否为空,即文件夹里是否有图片文件
        if self.img_paths:
            return True
        return False

    def get_img_index(self):
        """获取当前图片路径列表的索引"""
        # 判断图片路径列表是否为空
        if self.img_paths:  # 列表非空,索引有效
            return self.cur_img_index
        return None  # 列表为空,索引无效

    def get_img_path(self):
        """获取当前图片路径"""
        if self.img_paths:
            return self.img_paths[self.cur_img_index]
        return None

    def get_last_img_path(self):
        """获取上一张图片路径"""
        if len(self.img_paths) > 1:  # 图片路径列表长度大于1,可获取上一张图片
            return self.img_paths[self.cur_img_index - 1]
        return None  # 图片路径列表长度小于等于1,不可获取上一张图片

    def get_next_img_path(self):
        """获取下一张图片路径"""
        if len(self.img_paths) > 1:  # 图片路径列表长度大于1,可获取下一张图片
            return self.img_paths[self.cur_img_index + 1]
        return None  # 图片路径列表长度小于等于1,不可获取下一张图片

    def get_img_size(self):
        """获取当前图片尺寸"""
        if self.img_paths:  # 图片路径列表非空,即存在图片
            return self.img_width, self.img_height
        return None  # 图片路径列表为空,不存在图片

    def get_new_img(self):
        """获取当前图片"""
        if self.img_paths:  # 图片路径列表非空,可加载图片
            # 获取当前图片路径
            img_path = self.img_paths[self.cur_img_index]
            # 读取PIL图片
            self.pil_img = Image.open(img_path)
            # 创建可显示的图片对象
            self.tk_img = ImageTk.PhotoImage(self.pil_img)
            # 获取当前图片尺寸
            self.img_width, self.img_height = self.pil_img.size
            self.img_ratio = self.img_width / self.img_height
            # 返回当前图片
            return self.tk_img
        return None  # 图片路径列表为空,不存在图片

    def resize_img(self, max_width, max_height):
        """按比例缩放图片以适应画布"""
        if self.img_paths:  # 图片路径列表非空,存在图片
            # 根据画布的最大尺寸计算缩放后的大小
            new_width = int(max_height * self.img_ratio)
            if new_width > max_width:
                new_height = int(max_width / self.img_ratio)
                width, height = max_width, new_height
            else:
                width, height = new_width, max_height
            # 重新加载图片对象,防止多次缩放后图片质量降低
            self.pil_img = Image.open(self.img_paths[self.cur_img_index])
            # 使用PIL中的resize函数重新缩放图片大小
            self.pil_img = self.pil_img.resize((width, height))
            # 将PIL图片转换为cv2图片
            # self.cv_img = cv.cvtColor(np.array(self.pil_img), cv.COLOR_RGB2BGR)
            # 创建可显示的图片对象
            self.tk_img = ImageTk.PhotoImage(self.pil_img)
            # 更新图片尺寸
            self.img_width, self.img_height = self.pil_img.size
            # 返回缩放后的tk图片对象
            return self.tk_img
        return None  # 图片路径列表为空,不存在图片

    def get_prev_img(self):
        """返回上一张图片对象"""
        if self.img_paths:  # 图片路径列表非空,存在图片
            # 将当前图片索引减1,切换到上一张图片
            self.cur_img_index -= 1
            # 将当前图片索引取模,防止超出图片路径列表长度
            self.cur_img_index %= len(self.img_paths)
            # 返回上一张图片对象
            return self.get_new_img()
        return None  # 图片路径列表为空,不存在图片

    def get_next_img(self):
        """返回下一张图片对象"""
        if self.img_paths:  # 图片路径列表非空,存在图片
            # 将当前图片索引加1,切换到下一张图片
            self.cur_img_index += 1
            # 将当前图片索引取模,防止超出图片路径列表长度
            self.cur_img_index %= len(self.img_paths)
            # 返回下一张图片对象
            return self.get_new_img()
        return None  # 图片路径列表为空,不存在图片

    def del_img(self):
        """从列表中删除当前图片路径,并返回下一张图片"""
        # 删除图片路径
        self.img_paths.pop(self.cur_img_index)
        # 判断图片列表是否为空
        if self.img_paths:
            # 不为空,则将当前图片索引更新为下一张图片并返回
            return self.get_next_img()
        else:
            # 删除完之后空了,重新初始化所有图片对象和索引
            self.cur_img_index = 0
            self.pil_img = None
            self.cv_img = None
            self.tk_img = None
            return None
