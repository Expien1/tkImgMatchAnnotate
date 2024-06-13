# -*- coding: utf-8 -*-
import os


class LabelProcessor:
    """图片标签文件处理类"""
    def __init__(self):
        # 定义标签文件后缀
        self.label_suffix = 'txt'
        # 保存当前图片所标注的所有矩形框的yolo标签格式
        self.label_dict = dict()  # 矩形框id: (标签id, x_center, y_center, rect_width, rect_height)
        # 保存当前标签文件路径
        self.label_file_path = None

    def get_label_file_path(self, img_path):
        """从当前图片路径获取标签文件路径,如果找不到则返回None"""
        if img_path:
            label_file_path = img_path.rstrip(img_path.split('.')[-1]) + self.label_suffix
            if os.path.exists(label_file_path):
                return label_file_path
            else:
                return None
        else:
            return None

    def get_rect_from_label_file(self, label_file_path, img_width, img_height):
        """从标签文件路径中获取矩形框信息"""
        if label_file_path:
            with open(label_file_path, 'r') as f:
                return [self.yolo_str_to_rect(img_width, img_height, yolo_str)
                        for yolo_str in f.readlines()]
        else:
            return None

    def add_rect_to_label_file(self, img_width, img_height, label_id, x_start, y_start, x_end, y_end):
        """将矩形框标签写入标签文件"""
        # 将矩形框信息转换为yolo格式标签
        yolo_num = self.rect_to_yolo_num(img_width, img_height, label_id, x_start, y_start, x_end, y_end)
        yolo_str = f"{int(yolo_num[0])} {yolo_num[1]} {yolo_num[2]} {yolo_num[3]} {yolo_num[4]}\n"
        # 将yolo格式标签追加写入标签文件
        with open(self.label_file_path, 'a') as f:
            f.write(yolo_str)

    def update_label_file_path(self, img_path):
        """获取当前图片的标签文件路径"""
        if img_path:
            self.label_file_path = img_path.rstrip(img_path.split('.')[-1]) + self.label_suffix
        else:
            self.label_file_path = None
        return self.label_file_path

    def load_labels_to_rects(self, img_width, img_height):
        """加载当前图片中保存过的yolo标签,并将yolo标签转换为矩形框信息"""
        # 将yolo标签文件读取出来
        with open(self.label_file_path, 'r') as f:
            # 读取成二维列表, 每个列表保存了一个yolo标签
            return [self.yolo_str_to_rect(img_width, img_height, yolo_str)
                    for yolo_str in f.readlines()]

    def record_rect(self, img_width, img_height, rect_id, label_id, x_start, y_start, x_end, y_end):
        """保存矩形框标签至yolo标签格式"""
        self.label_dict[rect_id] = self.rect_to_yolo_num(img_width, img_height,
                                                         label_id, x_start, y_start, x_end, y_end)

    def clear_rect_dict(self):
        """清空当前图片的矩形框标签"""
        self.label_dict.clear()

    def get_rect_dict(self, img_width, img_height):
        """将yolo格式标签转换,然后返回为当前图片的所有矩形框信息,键为矩形框id,值为矩形框信息"""
        rect_dict = {ri: self.yolo_num_to_rect(img_width, img_height, li, xc, yc, w, h)
                     for ri, (li, xc, yc, w, h) in self.label_dict.items()}
        # 以下是该字典推导式的展开,两者是等价的
        # rect_dict = dict()
        # for ri, (li, xc, yc, w, h) in self.label_dict.items():
        #     rect_dict[ri] = self.yolo_num_to_rect(img_width, img_height, li, xc, yc, w, h)
        return rect_dict

    def save_label_file(self, rect_id, img_width, img_height):
        """将矩形框信息保存为yolo标签txt文件"""
        # 将矩形框信息转换为yolo格式标签
        yolo_label = self.yolo_num_to_str_by_id(img_width, img_height, rect_id)
        # 将yolo格式标签追加写入标签文件
        with open(self.label_file_path, 'a') as f:
            f.write(yolo_label)

    def adjust_label_file(self, rect_id, *, new_label_tuple=None, mode=None):
        """从标签文件中修改该id号的矩形框的标签
        mode为'delete'时删除该id号标签,mode为'modify'时修改该id号标签"""
        if mode == 'delete':  # 删除模式:删除该id号标签
            # 将需要删除的标签从字典中删除
            self.label_dict.pop(rect_id)
        elif mode == 'modify':  # 默认为修改模式:修改该id号标签
            lb, xc, yc, w, h = new_label_tuple  # 参数为(标签索引号, x_center, y_center, width, height)
            self.label_dict[rect_id] = int(lb), xc, yc, w, h  # 将新标签写入字典
        else:  # 错误模式
            print('mode参数错误')
            return  # 退出函数
        # 遍历标签字典,标签重新写入标签文件(使用覆盖写)
        with open(self.label_file_path, 'w') as f:
            for label_id, x_center, y_center, width, height in self.label_dict.values():
                f.write(f"{label_id} {x_center} {y_center} {width} {height}\n")

    def yolo_str_to_rect(self, img_width, img_height, yolo_str):
        """将yolo格式的字符串标签转换为矩形框信息"""
        yolo_label = yolo_str.rstrip('\n').split()
        label_id = int(yolo_label[0])  # 获取标签索引号
        x_center, y_center, rect_width, rect_height = (float(yolo_label[1]), float(yolo_label[2]),
                                                       float(yolo_label[3]), float(yolo_label[4]))
        x_start, y_start, x_end, y_end = self.xywh_to_xyxy(x_center, y_center, rect_width, rect_height)
        return label_id, *tuple(map(int, self.denormalization(img_width, img_height,
                                                              x_start, y_start, x_end, y_end)))

    def yolo_num_to_str_by_id(self, img_width, img_height, rect_id):
        """将矩形框字典里的yolo数值标签转换为yolo字符标签"""
        # 根据传入的矩形框id获取yolo格式的数值标签
        rect = self.label_dict[rect_id]
        return f"{int(rect[0])} {rect[1]} {rect[2]} {rect[3]} {rect[4]}\n"

    def yolo_num_to_rect(self, img_width, img_height,
                         label_id, x_center, y_center, rect_width, rect_height)->tuple:
        """将yolo格式的数字类型标签转换为矩形框信息"""
        # x_start, y_start, x_end, y_end = self.xywh_to_xyxy(x_center, y_center, rect_width, rect_height)
        # return label_id, *self.denormalization(img_width, img_height, x_start, y_start, x_end, y_end)
        x_center, y_center, rect_width, rect_height = self.denormalization(img_width, img_height,
                                                            x_center, y_center, rect_width, rect_height)
        return label_id, *map(int, self.xywh_to_xyxy(x_center, y_center, rect_width, rect_height))

    def rect_to_yolo_num(self, img_width, img_height,
                         label_id, x_start, y_start, x_end, y_end):
        """将矩形框转换为yolo格式"""
        # 将矩形框左上角坐标和右下角坐标转换为中心点坐标和宽高
        x_center, y_center, rect_width, rect_height = self.xyxy_to_xywh(x_start, y_start, x_end, y_end)
        x_center, y_center, rect_width, rect_height = self.normalization(img_width, img_height,
                                                                         x_center, y_center,
                                                                         rect_width, rect_height)
        return int(label_id), x_center, y_center, rect_width, rect_height

    def get_label_id(self, rect_id):
        """获取矩形框标签索引号"""
        return self.label_dict[rect_id][0]

    def get_rect_crood(self, rect_id, img_width, img_height):
        """获取矩形框左上角和右下角坐标"""
        li, xc, yc, w, h = self.label_dict[rect_id]
        li, xs, ys, xe, ye = self.yolo_num_to_rect(img_width, img_height, li, xc, yc, w, h)
        return xs, ys, xe, ye

    def get_center_label_crood(self, rect_id):
        """获取矩形框中心点归一化后的坐标"""
        x_center = self.label_dict[rect_id][1]
        y_center = self.label_dict[rect_id][2]
        return x_center, y_center

    def get_center_crood(self, rect_id, img_width, img_height):
        """获取矩形框在当前尺寸图片中的中心点坐标"""
        x_center = int(self.label_dict[rect_id][1] * img_width)
        y_center = int(self.label_dict[rect_id][2] * img_height)
        return x_center, y_center

    @staticmethod
    def xyxy_to_xywh(x_start, y_start, x_end, y_end):
        """将矩形框的左上角坐标和右下角坐标转换为中心点坐标和宽高"""
        x_center = (x_start + x_end) / 2
        y_center = (y_start + y_end) / 2
        width = x_end - x_start
        height = y_end - y_start
        return x_center, y_center, width, height

    @staticmethod
    def xywh_to_xyxy(x_center, y_center, width, height):
        """将矩形框的中心点坐标和宽高转换为左上角坐标和右下角坐标"""
        x_start = x_center - width / 2
        y_start = y_center - height / 2
        x_end = x_center + width / 2
        y_end = y_center + height / 2
        return x_start, y_start, x_end, y_end

    @staticmethod
    def normalization(img_width, img_height,
                      x_center, y_center, rect_width, rect_height):
        """将矩形框的坐标转换为归一化坐标"""
        x_center = x_center / img_width
        y_center = y_center / img_height
        rect_width = rect_width / img_width
        rect_height = rect_height / img_height
        return x_center, y_center, rect_width, rect_height

    @staticmethod
    def denormalization(img_width, img_height,
                        x_center, y_center, rect_width, rect_height):
        """将yolo格式标签反归一化"""
        x_center = x_center * img_width
        y_center = y_center * img_height
        rect_width = rect_width * img_width
        rect_height = rect_height * img_height
        return x_center, y_center, rect_width, rect_height


