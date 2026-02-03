import threading
import time

import numpy as np
import cv2 as cv
from PIL import Image


def get_pyramid(image, levels):
    """获取levels层的image的金字塔"""
    # 进行高斯模糊平滑处理,注意高斯平滑只能使用在原图一次
    processed_image = cv.GaussianBlur(image, (5, 5), -1)
    # 构建图像金字塔
    pyramid = []
    for l in range(0, levels):  # levels是你想要的金字塔层数
        # 进行下采样，这里使用了OpenCV的内置函数pyrDown
        processed_image = cv.pyrDown(processed_image)
        pyramid.append(processed_image)
    return pyramid  # 结果pyramid不包含原图像


def get_pyramid_till(image, min_width=128, min_height=128):
    """获取image直到满足最小尺寸为止的金字塔"""
    # 进行高斯模糊平滑处理,注意高斯平滑只能使用在原图一次
    processed_image = cv.GaussianBlur(image, (5, 5), -1)
    # 构建图像金字塔列表
    pyramid = [cv.pyrDown(processed_image)]
    while (pyramid[-1].shape[0] > min_height
           or pyramid[-1].shape[1] > min_width):
        pyramid.append(cv.pyrDown(pyramid[-1]))
    return pyramid


def rotate(image, angle):
    """旋转图像,并获取旋转后的掩码"""
    # 获取图像尺寸
    height, width = image.shape[:2]
    # 计算旋转中心点
    center = (width // 2, height // 2)
    # 获取旋转矩阵
    rotation_matrix = cv.getRotationMatrix2D(center, angle, 1.0)
    # 计算旋转后图像的边界框尺寸
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    # 调整旋转矩阵以适应新尺寸
    rotation_matrix[0, 2] += (new_width / 2) - center[0]
    rotation_matrix[1, 2] += (new_height / 2) - center[1]
    # 旋转图像并添加黑色边框
    rotated_image = cv.warpAffine(image, rotation_matrix, (new_width, new_height),
                                  borderMode=cv.BORDER_CONSTANT,
                                  borderValue=(0, 0, 0))
    # return rotated_image
    # 计算旋转后的掩码,
    gray_rotated = cv.cvtColor(rotated_image, cv.COLOR_BGR2GRAY)
    _, mask = cv.threshold(gray_rotated, 0, 255, cv.THRESH_BINARY)
    return rotated_image, mask


def match_by_angle(source, template, angle):
    """旋转模板并进行模板匹配,返回最大匹配值和匹配位置"""
    rotated_template, template_mask = rotate(template, angle)  # 旋转模板,并获取旋转后的掩码
    # 进行模板匹配,使用掩码来排除黑边
    res = cv.matchTemplate(source, rotated_template, cv.TM_CCOEFF_NORMED, mask=template_mask)
    # 将匹配结果里面的NaN和Inf值替换为0,不知道为什么有时候匹配结果会出现nan和inf值,所以替换掉
    nan_mask = np.isnan(res)  # 获取NaN的位置掩码
    res = np.where(nan_mask, 0, res)  # 将找到的NaN位置的值替换为0
    inf_mask = np.isinf(res)  # 获取Inf的位置掩码
    res = np.where(inf_mask, 0, res)  # 将找到的Inf位置的值替换为0
    _, max_similarity, _, max_location = cv.minMaxLoc(res)  # 获取该旋转角度的最大相似度
    return max_similarity, max_location  # 返回最大相似度和匹配位置


def get_rect(template, match_location):
    """计算匹配后的矩形框坐标"""
    template_height, template_width = template.shape[:2]  # 获取模板图像的尺寸
    x, y = match_location  # 获取匹配位置
    return x, y, (x + template_width), (y + template_height)  # 返回矩形框坐标


def adjust_rect(source, template, match_location, extra_rate=0.05):
    """将匹配后的矩形框扩大一定比例,再调整到图片边缘"""
    # 获取图像的尺寸
    source_height, source_width = source.shape[:2]
    # 获取匹配后的矩形框坐标
    xs, ys, xe, ye = get_rect(template, match_location)
    # 扩大矩形框,计算扩大后的矩形框坐标
    extra_xy = max(xe - xs, ye - ys) // (extra_rate * 100)
    x_start, y_start = xs - extra_xy, ys - extra_xy
    x_end, y_end = xe + extra_xy, ye + extra_xy
    # 防止超出图片边界
    x_start, y_start = int(max(0, x_start)), int(max(0, y_start))
    x_end, y_end = int(min(source_width, x_end)), int(min(source_height, y_end))
    # cv.rectangle(source, (x_start, y_start), (x_end, y_end), (255, 0, 0), 2)
    # 简单的直方图均衡化提高对比度
    img = cv.cvtColor(source[y_start:y_end, x_start:x_end], cv.COLOR_BGR2GRAY)
    img = cv.equalizeHist(img)
    # 自动阈值处理（Otsu's二值化）
    _, thresh = cv.threshold(img, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    # 形态学操作：先腐蚀后膨胀，去除小噪点并闭合轮廓
    kernel = np.ones((9, 9), np.uint8)
    opening = cv.morphologyEx(thresh, cv.MORPH_OPEN, kernel)
    closing = cv.morphologyEx(opening, cv.MORPH_CLOSE, kernel)
    # cv.imshow("closing", closing)
    # 寻找轮廓
    contours, _ = cv.findContours(closing, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # 找到最大轮廓（假设为中心物体）
    if contours:
        max_contour = max(contours, key=cv.contourArea)
        # 获取最小外接矩形
        x, y, w, h = cv.boundingRect(max_contour)
        # 转换并返回调整后的矩形框坐标
        return (x_start + x), (y_start + y), (x_start + x + w), (y_start + y + h)
        # 在原图上画出矩形框
        # cv.rectangle(source, (x_start+x, y_start+y), (x_start+x + w, y_start+y + h), (0, 255, 255), 3)
        # cv.imshow("Match Result extra", source)
    else:  # 如果没有找到轮廓，则返回原始的矩形框坐标
        return xs, ys, xe, ye


def coarse_match(source, template, step=5):
    """使用金字塔图像最顶层的图片进行一次粗略匹配,并记录下最佳相似度和位置以及最佳旋转角度"""
    # 获取图像金字塔的顶层,将最小尺寸稍微提升
    source_pyramid = get_pyramid_till(source, 256, 256)
    levels = len(source_pyramid)
    template = get_pyramid(template, levels)[-1]
    source = source_pyramid[-1]
    # 记录最佳相似度和其对应的位置
    best_similarity = 0
    best_location = (0, 0)
    best_angle = 0
    # 对顶层的图像进行旋转模板匹配
    for angle in range(0, 361, step):
        # 进行模板匹配
        max_similarity, max_location = match_by_angle(source, template, angle)
        if max_similarity > best_similarity:  # 如果当前相似度大于最佳相似度
            best_similarity = max_similarity  # 更新最佳相似度
            best_location = max_location  # 更新最佳位置
            best_angle = angle  # 更新最佳旋转角度
    return best_similarity, best_location, best_angle  # 返回最佳相似度,最佳位置和最佳旋转角度


def coarse_fine_match(source, template, higher_similarity=False, adjust_result=True, match_event=None):
    """
    粗匹配(Coarse Matching)确认旋转角度,确定旋转角度之后再进行精匹配(Fine Registration)
    source为被匹配的图像,template为模板图像
    match_event: 用于取消匹配的Event对象
    """
    # 如果没有传入Event，创建一个不取消的Event
    if match_event is None:
        match_event = threading.Event()

    # 检查是否需要取消
    if match_event.is_set():
        return None

    # 构建图像金字塔来逐步进行匹配,降低计算复杂度
    source_pyramid = get_pyramid_till(source, 128, 128)
    levels = len(source_pyramid)
    template_pyramid = get_pyramid(template, levels)

    # 检查是否需要取消
    if match_event.is_set():
        return None

    angle_dict = dict()
    for angle in range(0, 361, 5):
        # 检查是否需要取消
        if match_event.is_set():
            return None
        max_similarity, max_location = match_by_angle(source_pyramid[-1], template_pyramid[-1], angle)
        angle_dict[angle] = max_similarity

    for level in range(levels - 2, -1, -1):
        if match_event.is_set():
            return None
        angle_num = level + 1
        better_angle_ls = sorted(angle_dict.keys(), key=lambda x: angle_dict[x], reverse=True)[:angle_num]
        angle_dict.clear()
        for angle in better_angle_ls:
            for around in range(-5, 6, 1):
                if match_event.is_set():
                    return None
                around_angle = angle + (around * (0.3 ** ((levels - 1) - level)))
                max_similarity, max_location = match_by_angle(source_pyramid[-1],
                                                              template_pyramid[-1], angle)
                angle_dict[around_angle] = max_similarity

    if match_event.is_set():
        return None

    best_angle = max(angle_dict.keys(), key=lambda x: angle_dict[x])
    last_similarity = angle_dict[best_angle]
    source = cv.GaussianBlur(source, (5, 5), -1)
    template = cv.GaussianBlur(template, (5, 5), -1)
    rotated_template, template_mask = rotate(template, best_angle)
    res = cv.matchTemplate(source, rotated_template, cv.TM_CCOEFF_NORMED, mask=template_mask)
    _, cur_similarity, _, max_location = cv.minMaxLoc(res)
    print("最佳角度:", best_angle, "最佳相似度:", cur_similarity, "上一层最佳相似度:", last_similarity)
    max_similarity = max(cur_similarity, last_similarity) if higher_similarity else cur_similarity
    x_start, y_start, x_end, y_end = (adjust_rect(source, rotated_template, max_location)
                                      if adjust_result else get_rect(rotated_template, max_location))
    return max_similarity, x_start, y_start, x_end, y_end


def draw_result(source, temp, match_point):
    """
    在原图像上绘制匹配结果
    """
    # 获取模板图像的尺寸
    template_height, template_width = temp.shape[:2]
    # 获取匹配点坐标
    x, y = match_point
    # 绘制矩形框
    cv.rectangle(source, (x, y), (x + template_width, y + template_height), (0, 0, 255), 3)
    # 显示匹配结果
    cv.imshow("Match Result", source)


def match_by_angle_and_level(source, template, angle, level):
    """使用指定的角度和层数进行模板匹配"""
    source_pyramid = get_pyramid(source, level)  # 获取指定层的图像金字塔
    template_pyramid = get_pyramid(template, level)
    return match_by_angle(source_pyramid[-1], template_pyramid[-1], angle)


class TemplateManager:
    """模板管理类"""
    def __init__(self, image_processor, label_processor, status_bar=None):
        self.image_processor = image_processor
        self.label_processor = label_processor
        self.status_bar = status_bar
        # 模板字典格式,键为类别,值为列表,列表中元素为(模板的np对象,对应的系数),系数用于筛选模板
        self.template_dict = dict()  # (模板, 系数)这里的系数是一个模板的衰减值,相当于一个模板的年龄
        self.max_template_num = 10  # 定义最大模板数量
        self.threshold = 0.7  # 定义匹配阈值
        self.higher_similarity = True  # 是否使用较大的相似度
        self.adjust_result = True  # 是否需要自动调整匹配位置
        self.DECAY_FACTOR = 0.9  # 模板衰减系数
        self.last_templ_id_dict = dict()  # 记录上一次使用过的匹配的模板字典,键为类别,值为模板id

    def set_max_template_num(self, new_max_template_num):
        """设置最大保存的模板数量"""
        if 1 <= new_max_template_num <= 30:
            self.max_template_num = new_max_template_num
        self.status_bar.txshow("成功设置最大模板数量为" + str(self.max_template_num), 3)
        return self.max_template_num

    def get_max_template_num(self):
        """获取最大保存的模板数量"""
        return self.max_template_num

    def set_threshold(self, new_threshold):
        """设置匹配阈值"""
        if 0 < self.threshold < 1:
            self.threshold = new_threshold
        self.status_bar.txshow("成功设置匹配阈值为" + str(self.threshold), 3)
        return self.threshold

    def get_threshold(self):
        """获取匹配阈值"""
        return self.threshold

    def set_higher_similarity(self, higher_similarity):
        """设置是否使用较大的相似度"""
        self.higher_similarity = higher_similarity
        self.status_bar.txshow("已更新使用更高的匹配相似度的设置,注意:匹配精度并不会提升", 3)
        return self.higher_similarity

    def get_higher_similarity(self):
        """获取当前是否使用较大的相似度的设置"""
        return self.higher_similarity

    def set_adjust_result(self, adjust_result):
        """设置是否需要自动调整匹配位置"""
        self.adjust_result = adjust_result
        self.status_bar.txshow("已更新自动调整匹配位置的设置", 3)
        return self.adjust_result

    def get_adjust_result(self):
        """获取当前是否需要自动调整匹配位置的设置"""
        return self.adjust_result

    def update_template(self, label_id, template):
        """按照一定策略移除模板,然后添加新模板"""
        # 移除系数最低的模板
        self.template_dict[label_id].sort(key=lambda x: x[1])  # 对模板列表按系数进行排序
        self.template_dict[label_id].pop(0)  # 将系数最低的模板移除
        self.template_dict[label_id].append([template, 1])  # 将新模板添加到列表中

    def load_template(self, img_path):
        """加载指定路径下的图片作为模板"""
        # 获取对应的标签文件路径
        label_file_path = self.label_processor.get_label_file_path(img_path)
        # 判断该图片的标签文件是否存在
        if label_file_path:  # get_label_file_path方法返回None则说明该图片没有对应的标签文件
            # 先读取图片文件
            img_pil = Image.open(img_path)  # 使用PIL读取图片文件,因为cv无法读取中文路径
            image = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
            img_height, img_width = image.shape[:2]  # 获取图片的宽高
            # 读取标签文件里的标签并转换为矩形框坐标
            label_ls = self.label_processor.get_rect_from_label_file(label_file_path,
                                                                     img_width, img_height)
            # 遍历该图片的标签,保存成模板
            for label_id, x_start, y_start, x_end, y_end in label_ls:
                template = image[y_start:y_end, x_start:x_end]  # 根据标签内容裁切出对应的模板
                # 判断该类别是否已经存进模板字典中
                if self.template_dict.get(label_id, None) is not None:
                    # 判断该类别的模板列表是否已经满了
                    if len(self.template_dict[label_id]) >= self.max_template_num:
                        self.update_template(label_id, template)  # 将新的模板更新到该类别的模板列表中
                    else:  # 没满就直接添加模板
                        self.template_dict[label_id].append([template, 1])  # 将模板保存到字典中
                else:  # 如果该类别还没有存进字典中,则新建一个列表,并将模板保存进去
                    self.template_dict[label_id] = [[template, 1]]

    def load_all_templates(self):
        """加载当前文件夹下已经标注好的匹配模板"""
        # 遍历当前文件夹下的所有图片文件和对应的标签文件,然后加载模板
        for img_path in self.image_processor.img_paths:
            self.load_template(img_path)
        self.status_bar.txshow("成功从标签文件中加载已存在的模板", 3)

    def delete_last_template(self, label_id):
        """删除上一次匹配得到某标签的模板"""
        # 在上一次匹配的模板字典中查找并删除该模板
        if self.last_templ_id_dict.get(label_id, None) is not None:
            # 删除该标签对应的模板id
            self.template_dict[label_id].pop(self.last_templ_id_dict[label_id])
            self.last_templ_id_dict[label_id] = None

    def coarse_match_all_classes(self, img_path, match_event=None):
        """使用所有模板的金字塔的最顶层来粗略匹配一张图片,返回最佳相似度的模板
        match_event: 用于取消匹配的Event对象
        """
        # 如果没有传入Event，创建一个不取消的Event
        if match_event is None:
            match_event = threading.Event()

        img_pil = Image.open(img_path)
        image = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
        best_template_dict = dict()
        better_template_dict = dict()
        for label_id, template_ls in self.template_dict.items():
            if match_event.is_set():
                return None, None
            best_similarity = -1
            better_similarity = -1
            for idx, template in enumerate(template_ls):
                if match_event.is_set():
                    return None, None
                similarity, _, angle = coarse_match(image, template[0])
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_template_dict[label_id] = (idx, angle)
                else:
                    if similarity > better_similarity:
                        better_similarity = similarity
                        better_template_dict[label_id] = (idx, angle)
        return best_template_dict, better_template_dict

    def match_all_classes(self, img_path=None, match_event=None):
        """匹配所有类别的模板
        match_event: 用于取消匹配的Event对象
        """
        # 如果没有传入Event，创建一个不取消的Event
        if match_event is None:
            match_event = threading.Event()

        res_ls = []
        if img_path is None:
            img_path = self.image_processor.get_img_path()
        img_pil = Image.open(img_path)
        image = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
        img_height, img_width = image.shape[:2]
        # 使用粗匹配获取最佳模板字典和第二大相似度模板字典
        best_template_dict, better_template_dict = self.coarse_match_all_classes(img_path, match_event)

        # 检查是否被取消
        if best_template_dict is None or match_event.is_set():
            return []

        for label_id in best_template_dict.keys():
            if match_event.is_set():
                return []
            best_template = best_template_dict.get(label_id, None)
            better_template = better_template_dict.get(label_id, None)
            # 检查模板列表是否还存在，避免线程安全问题
            if label_id not in self.template_dict:
                continue
            template_ls = self.template_dict[label_id]
            if better_template is not None:
                # 检查索引是否有效
                if best_template[0] >= len(template_ls) or better_template[0] >= len(template_ls):
                    continue
                template_best = self.template_dict[label_id][best_template[0]][0]
                template_better = self.template_dict[label_id][better_template[0]][0]
                angle_of_best = best_template[1]
                angle_of_better = better_template[1]
                similarity_of_best, _ = match_by_angle_and_level(image, template_best,
                                                                 angle_of_best, 1)
                similarity_of_better, _ = match_by_angle_and_level(image, template_better,
                                                                   angle_of_better, 1)
                print('best:', similarity_of_best, 'better:', similarity_of_better)
                best_template_idx = best_template[0]
                better_template_idx = better_template[0]
                template = template_best
                if similarity_of_better > similarity_of_best:
                    template = template_better
                    self.template_dict[label_id][best_template_idx][1] *= self.DECAY_FACTOR
                    self.last_templ_id_dict[label_id] = better_template_idx
                else:
                    self.template_dict[label_id][better_template_idx][1] *= self.DECAY_FACTOR
                    self.last_templ_id_dict[label_id] = best_template_idx

                # 检查是否被取消
                if match_event.is_set():
                    return []

                # 检查模板是否有效
                if template is None:
                    continue

                max_similarity, x_start, y_start, x_end, y_end = coarse_fine_match(image, template,
                                                                                   self.higher_similarity,
                                                                                   self.adjust_result,
                                                                                   match_event)

                # 检查是否被取消
                if max_similarity is None or match_event.is_set():
                    return []

                self.status_bar.txshow(f'已完成所有模板的匹配,本次匹配的相似度为{max_similarity:3f}', 5)
                if max_similarity >= self.threshold:
                    res_ls.append(self.label_processor.rect_to_yolo_num(img_width, img_height, label_id,
                                                                        x_start, y_start, x_end, y_end))
            else:
                best_template_idx = best_template[0]
                # 检查索引是否有效
                if best_template_idx >= len(self.template_dict[label_id]):
                    continue
                template = self.template_dict[label_id][best_template_idx][0]
                self.last_templ_id_dict[label_id] = best_template_idx

                # 检查是否被取消
                if match_event.is_set():
                    return []

                # 检查模板是否有效
                if template is None:
                    continue

                max_similarity, x_start, y_start, x_end, y_end = coarse_fine_match(image, template,
                                                                                   self.higher_similarity,
                                                                                   self.adjust_result,
                                                                                   match_event)

                # 检查是否被取消
                if max_similarity is None or match_event.is_set():
                    return []

                self.status_bar.txshow(f'已完成所有模板的匹配,本次匹配的相似度为{max_similarity:3f}', 5)
                if max_similarity >= self.threshold:
                    res_ls.append(self.label_processor.rect_to_yolo_num(img_width, img_height, label_id,
                                                                        x_start, y_start, x_end, y_end))
        return res_ls


if __name__ == '__main__':
    img_pil = Image.open('./test_img/test_cv/4.jpg')  # 使用PIL读取图片文件,因为cv无法读取中文路径
    img1 = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
    img_pil = Image.open('./test_img/test_cv/t0.jpg')  # 使用PIL读取图片文件,因为cv无法读取中文路径
    template = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

    t1 = time.time()
    coarse_fine_match(img1, template)
    print("time:", time.time() - t1)
    cv.waitKey(0)
    cv.destroyAllWindows()
