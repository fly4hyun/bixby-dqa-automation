###################################################################################################
###################################################################################################

import sys, os
import argparse
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QSplitter,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QLineEdit,
    QTableWidget, QTableWidgetItem, QWidget, QComboBox, QShortcut
)
from PyQt5.QtGui import QPixmap, QPen, QColor, QPainter, QKeySequence, QTransform
from PyQt5.QtCore import Qt, QRectF, QEvent, QTimer
from PyQt5.QtWidgets import QGraphicsRectItem

###################################################################################################
###################################################################################################

def parse_opt():
    parser = argparse.ArgumentParser()
    
    ###############################################################################################
    ### 라벨 이미지 폴더 위치
    parser.add_argument('--label_path', type=str, default='temp_data')

    opt = parser.parse_args()
    return opt

###################################################################################################
###################################################################################################
### CustomTableWidget: 오른쪽 박스 목록에서 방향키 이벤트 무시
class CustomTableWidget(QTableWidget):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            event.ignore()
        else:
            super().keyPressEvent(event)

###################################################################################################
###################################################################################################
### ResizableRectItem: 박스 크기 조절 아이템
class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsRectItem.ItemIsSelectable |
            QGraphicsRectItem.ItemIsMovable |
            QGraphicsRectItem.ItemIsFocusable |
            QGraphicsRectItem.ItemSendsGeometryChanges
        )
        self.handle_size = 8
        self.mouse_press_pos = None
        self.mouse_press_rect = None
        self.resize_mode = None

    def hoverMoveEvent(self, event):
        pos = event.pos()
        rect = self.rect()
        margin = self.handle_size
        left = abs(pos.x() - rect.left()) <= margin
        right = abs(pos.x() - rect.right()) <= margin
        top = abs(pos.y() - rect.top()) <= margin
        bottom = abs(pos.y() - rect.bottom()) <= margin
        cursor = Qt.ArrowCursor
        self.resize_mode = None
        if top and left:
            cursor = Qt.SizeFDiagCursor
            self.resize_mode = "top_left"
        elif top and right:
            cursor = Qt.SizeBDiagCursor
            self.resize_mode = "top_right"
        elif bottom and left:
            cursor = Qt.SizeBDiagCursor
            self.resize_mode = "bottom_left"
        elif bottom and right:
            cursor = Qt.SizeFDiagCursor
            self.resize_mode = "bottom_right"
        elif left:
            cursor = Qt.SizeHorCursor
            self.resize_mode = "left"
        elif right:
            cursor = Qt.SizeHorCursor
            self.resize_mode = "right"
        elif top:
            cursor = Qt.SizeVerCursor
            self.resize_mode = "top"
        elif bottom:
            cursor = Qt.SizeVerCursor
            self.resize_mode = "bottom"
        else:
            cursor = Qt.SizeAllCursor
            self.resize_mode = None
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self.mouse_press_pos = event.pos()
        self.mouse_press_rect = self.rect()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resize_mode is not None:
            diff = event.pos() - self.mouse_press_pos
            rect = self.mouse_press_rect
            new_rect = QRectF(rect)
            if self.resize_mode == "left":
                new_rect.setLeft(rect.left() + diff.x())
            elif self.resize_mode == "right":
                new_rect.setRight(rect.right() + diff.x())
            elif self.resize_mode == "top":
                new_rect.setTop(rect.top() + diff.y())
            elif self.resize_mode == "bottom":
                new_rect.setBottom(rect.bottom() + diff.y())
            elif self.resize_mode == "top_left":
                new_rect.setTopLeft(rect.topLeft() + diff)
            elif self.resize_mode == "top_right":
                new_rect.setTopRight(rect.topRight() + diff)
            elif self.resize_mode == "bottom_left":
                new_rect.setBottomLeft(rect.bottomLeft() + diff)
            elif self.resize_mode == "bottom_right":
                new_rect.setBottomRight(rect.bottomRight() + diff)
            if new_rect.width() < 10:
                new_rect.setWidth(10)
            if new_rect.height() < 10:
                new_rect.setHeight(10)
            self.setRect(new_rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resize_mode = None
        super().mouseReleaseEvent(event)

###################################################################################################
###################################################################################################
### ImageLabelAnnotator: 메인 윈도우
class ImageLabelAnnotator(QMainWindow):
    def __init__(self, opt):
        super().__init__()
        self.setWindowTitle("Image Label Annotator (라벨 텍스트 파일 수정)")
        self.setGeometry(100, 100, 2048, 1152)
        self.setFocusPolicy(Qt.StrongFocus)

        ### 방향키 단축키 (항상 동작)
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcut_left.activated.connect(lambda: self.deferDirectionKey(Qt.Key_Left))
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcut_right.activated.connect(lambda: self.deferDirectionKey(Qt.Key_Right))
        self.shortcut_up = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcut_up.activated.connect(lambda: self.deferDirectionKey(Qt.Key_Up))
        self.shortcut_down = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_down.activated.connect(lambda: self.deferDirectionKey(Qt.Key_Down))

        self.temp_data_folder = opt.label_path
        self.pdf_combo = QComboBox()
        if os.path.exists(self.temp_data_folder):
            pdf_dirs = [d for d in os.listdir(self.temp_data_folder)
                        if os.path.isdir(os.path.join(self.temp_data_folder, d))]
            self.pdf_combo.addItems(pdf_dirs)
        self.pdf_combo.currentTextChanged.connect(self.change_pdf_folder)

        self.pdf_name = self.pdf_combo.currentText() if self.pdf_combo.count() > 0 else ""
        self.base_folder = os.path.join(self.temp_data_folder, self.pdf_name)
        self.ori_images_folder = os.path.join(self.base_folder, "ori_images")
        self.labels_folder = os.path.join(self.base_folder, "labels")

        self.image_files = []
        self.current_index = 0

        self.is_drawing = False
        self.drawing_box = None
        self.start_point = None
        self.current_image_path = None
        self.iw = 0
        self.ih = 0
        self.drawn_boxes = []

        self.class_list = [
            "대제목", "섹션 박스", "중제목", "소제목", "내용", "이미지/표 박스",
            "이미지", "표", "아이콘_내용", "페이지 번호", "아이콘", "목차"
        ]
        self.current_class_index = 0
        self.class_colors = [
            "#FF4500", "#1E90FF", "#FF1493", "#32CD32", "#FFD700", "#8B008B",
            "#00CED1", "#FF8C00", "#9400D3", "#FF1493", "#696969", "#8B4513"
        ]

        self.splitter = QSplitter()

        ### 왼쪽 패널: PDF 폴더 선택 및 이미지 목록
        self.left_layout = QVBoxLayout()
        self.left_layout.addWidget(QLabel("PDF 폴더 선택"))
        self.left_layout.addWidget(self.pdf_combo)
        self.image_list = QListWidget()
        self.left_layout.addWidget(QLabel("이미지 목록"))
        self.left_layout.addWidget(self.image_list)
        left_widget = QWidget()
        self.left_layout.setContentsMargins(5, 5, 5, 5)
        left_widget.setLayout(self.left_layout)

        ### 가운데 패널: 이미지 뷰 및 페이지 컨트롤
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.page_control_layout = QHBoxLayout()
        self.previous_button = QPushButton("이전 페이지")
        self.page_input = QLineEdit("1")
        self.page_input.setFixedWidth(50)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.next_button = QPushButton("다음 페이지")
        self.page_control_layout.addWidget(self.previous_button)
        self.page_control_layout.addWidget(self.page_input)
        self.page_control_layout.addWidget(self.next_button)
        center_layout = QVBoxLayout()
        center_layout.addWidget(self.view)
        center_layout.addLayout(self.page_control_layout)
        center_widget = QWidget()
        center_widget.setLayout(center_layout)

        ### 오른쪽 패널: 클래스 선택, 박스 목록, 박스 이동 및 라벨 저장/수정 버튼
        self.right_layout = QVBoxLayout()
        self.selected_class_label = QLabel("현재 클래스: (none)")
        class_line1 = QHBoxLayout()
        class_line2 = QHBoxLayout()
        class_line3 = QHBoxLayout()
        for i in range(5):
            btn = QPushButton(f"{i}: {self.class_list[i]}")
            btn.clicked.connect(lambda _, idx=i: self.set_current_class(idx))
            class_line1.addWidget(btn)
        for i in range(5, 10):
            if i < len(self.class_list):
                btn = QPushButton(f"{i}: {self.class_list[i]}")
                btn.clicked.connect(lambda _, idx=i: self.set_current_class(idx))
                class_line2.addWidget(btn)
        if len(self.class_list) > 10:
            for i in range(10, len(self.class_list)):
                btn = QPushButton(f"{i}: {self.class_list[i]}")
                btn.clicked.connect(lambda _, idx=i: self.set_current_class(idx))
                class_line3.addWidget(btn)
        self.box_table = CustomTableWidget()
        self.box_table.setColumnCount(5)
        self.box_table.setHorizontalHeaderLabels(["클래스", "X_center_norm", "Y_center_norm", "w_norm", "h_norm"])
        self.box_table.itemChanged.connect(self.on_table_item_changed)
        self.box_table.itemSelectionChanged.connect(self.on_box_table_selectionChanged)
        self.save_button = QPushButton("S (라벨 저장)")
        self.delete_box_button = QPushButton("선택 박스 삭제")
        self.move_up_button = QPushButton("박스 위로 이동")
        self.move_down_button = QPushButton("박스 아래로 이동")
        self.move_completed_button = QPushButton("M (라벨 수정)")
        self.right_layout.addWidget(QLabel("클래스 선택 (숫자키 0~9)"))
        self.right_layout.addWidget(self.selected_class_label)
        self.right_layout.addLayout(class_line1)
        self.right_layout.addLayout(class_line2)
        if class_line3.count() > 0:
            self.right_layout.addLayout(class_line3)
        self.right_layout.addWidget(QLabel("박스 목록"))
        self.right_layout.addWidget(self.box_table)
        self.right_layout.addWidget(self.delete_box_button)
        move_btns_layout = QHBoxLayout()
        self.move_up_button.setMinimumWidth(100)
        self.move_down_button.setMinimumWidth(100)
        move_btns_layout.addWidget(self.move_up_button)
        move_btns_layout.addWidget(self.move_down_button)
        self.right_layout.addLayout(move_btns_layout)
        self.right_layout.addWidget(self.save_button)
        self.right_layout.addWidget(self.move_completed_button)
        right_widget = QWidget()
        self.right_layout.setContentsMargins(5, 5, 5, 5)
        right_widget.setLayout(self.right_layout)

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([200, 1200, 400])
        self.setCentralWidget(self.splitter)

        self.image_list.itemClicked.connect(self.list_item_clicked)
        self.previous_button.clicked.connect(self.previous_image)
        self.next_button.clicked.connect(self.next_image)
        self.page_input.returnPressed.connect(self.go_to_page)
        self.save_button.clicked.connect(self.save_annotations)
        self.delete_box_button.clicked.connect(self.delete_selected_box)
        self.move_up_button.clicked.connect(self.move_box_up)
        self.move_down_button.clicked.connect(self.move_box_down)
        self.move_completed_button.clicked.connect(self.copy_current_image_label)
        self.view.viewport().installEventFilter(self)

        if self.class_list:
            self.set_current_class(0)
        self.load_image_files()
        self.setFocus()

    ### add_box 메서드: 정규화된 사각형(normRect)와 클래스 인덱스를 받아 박스를 추가
    def add_box(self, normRect, cls_idx):
        x_center_norm = normRect.x()
        y_center_norm = normRect.y()
        w_norm = normRect.width()
        h_norm = normRect.height()
        w = w_norm * self.iw
        h = h_norm * self.ih
        cx = x_center_norm * self.iw
        cy = y_center_norm * self.ih
        x = cx - w/2
        y = cy - h/2
        rect = QRectF(x, y, w, h)
        group_item = self.draw_box_with_label(rect, cls_idx)
        self.add_box_to_table(cls_idx, QRectF(x_center_norm, y_center_norm, w_norm, h_norm), group_item)
        self.drawn_boxes.append((group_item, rect))
        self.resequence_boxes()

    def deferDirectionKey(self, key):
        QTimer.singleShot(0, lambda: self.processDirectionKey(key))

    def processDirectionKey(self, key):
        self.box_table.blockSignals(True)
        self.remove_all_highlights()
        self.box_table.clearSelection()
        self.box_table.blockSignals(False)
        if key == Qt.Key_Left:
            self.previous_image()
        elif key == Qt.Key_Right:
            self.next_image()
        elif key == Qt.Key_Up:
            self.previous_image()
        elif key == Qt.Key_Down:
            self.next_image()

    def remove_all_highlights(self):
        self.box_table.clearSelection()
        for row in range(self.box_table.rowCount()):
            cls_item = self.box_table.item(row, 0)
            if cls_item:
                data = cls_item.data(Qt.UserRole)
                if data:
                    group_item, _ = data
                    self.highlight_box(group_item, False)

    def highlight_box(self, group_item, highlight):
        try:
            children = group_item.childItems()
        except Exception as e:
            print("highlight_box error:", e)
            return
        for child in children:
            if child.data(0) is not None:
                if highlight:
                    child.setPen(QPen(QColor("red"), 5))
                else:
                    cls_idx = child.data(0)
                    if cls_idx is None:
                        continue
                    color_str = self.class_colors[cls_idx % len(self.class_colors)]
                    child.setPen(QPen(QColor(color_str), 3))  # 테두리 두께 2로 유지

    def on_box_table_selectionChanged(self):
        for row in range(self.box_table.rowCount()):
            cls_item = self.box_table.item(row, 0)
            if cls_item:
                data = cls_item.data(Qt.UserRole)
                if data:
                    group_item, _ = data
                    self.highlight_box(group_item, False)
        selected_rows = set(item.row() for item in self.box_table.selectedItems())
        for row in selected_rows:
            cls_item = self.box_table.item(row, 0)
            if cls_item:
                data = cls_item.data(Qt.UserRole)
                if data:
                    group_item, _ = data
                    self.highlight_box(group_item, True)

    def change_pdf_folder(self, pdf_name):
        self.pdf_name = pdf_name
        self.base_folder = os.path.join(self.temp_data_folder, self.pdf_name)
        self.ori_images_folder = os.path.join(self.base_folder, "ori_images")
        self.labels_folder = os.path.join(self.base_folder, "labels")
        self.load_image_files()

    def load_image_files(self):
        if not os.path.exists(self.ori_images_folder):
            os.makedirs(self.ori_images_folder)
        all_files = os.listdir(self.ori_images_folder)
        image_files = [f for f in all_files if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]
        try:
            image_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        except Exception:
            image_files.sort(key=lambda x: x.lower())
        self.image_files = image_files
        self.image_list.clear()
        for name in self.image_files:
            self.image_list.addItem(name)
        self.current_index = 0
        if self.image_files:
            self.show_imageByIndex(0)

    def list_item_clicked(self):
        row = self.image_list.currentRow()
        self.current_index = row
        self.show_imageByIndex(row)

    def show_imageByIndex(self, idx):
        if idx < 0 or idx >= len(self.image_files):
            return
        self.current_index = idx
        image_name = self.image_files[idx]
        image_path = os.path.join(self.ori_images_folder, image_name)
        self.load_image(image_path)
        self.page_input.setText(str(idx + 1))

    def load_image(self, image_path):
        self.current_image_path = image_path
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"[오류] 이미지를 열 수 없습니다: {image_path}")
            return
        self.scene.clear()
        self.iw = pixmap.width()
        self.ih = pixmap.height()
        
        ### QGraphicsScene에 픽스맵 추가하고, QGraphicsPixmapItem을 받음
        pixmap_item = self.scene.addPixmap(pixmap)
        
        ### 뷰포트 크기에 따른 스케일 값 계산
        scale_factor = min(self.view.viewport().width() / self.iw,
                        self.view.viewport().height() / self.ih)
        ### 확대(원본보다 크게 보일 때)는 최근접 보간(빠른 보간)을, 축소는 부드러운 보간을 사용
        if scale_factor > 1:
            pixmap_item.setTransformationMode(Qt.FastTransformation)
        else:
            pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        
        self.scene.setSceneRect(0, 0, self.iw, self.ih)
        self.view.setTransform(QTransform().scale(scale_factor, scale_factor))
        
        self.box_table.setRowCount(0)
        self.drawn_boxes.clear()
        label_name = os.path.splitext(os.path.basename(image_path))[0] + ".txt"
        label_path = os.path.join(self.labels_folder, label_name)
        if os.path.exists(label_path):
            with open(label_path, "r", encoding="utf-8") as f:
                for line in f:
                    vals = line.strip().split()
                    if len(vals) != 5:
                        continue
                    cls_str, x_str, y_str, w_str, h_str = vals
                    try:
                        cls_idx = int(cls_str)
                        x_center = float(x_str)
                        y_center = float(y_str)
                        w_norm = float(w_str)
                        h_norm = float(h_str)
                    except:
                        continue
                    w = w_norm * self.iw
                    h = h_norm * self.ih
                    cx = x_center * self.iw
                    cy = y_center * self.ih
                    x = cx - w/2
                    y = cy - h/2
                    rect = QRectF(x, y, w, h)
                    group_item = self.draw_box_with_label(rect, cls_idx)
                    group_item.setZValue(10000 - y)
                    self.add_box_to_table(cls_idx, QRectF(x_center, y_center, w_norm, h_norm), group_item)
        self.resequence_boxes()

    def previous_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_imageByIndex(self.current_index)

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.show_imageByIndex(self.current_index)

    def go_to_page(self):
        try:
            page_num = int(self.page_input.text()) - 1
            if 0 <= page_num < len(self.image_files):
                self.show_imageByIndex(page_num)
        except ValueError:
            pass

    def copy_current_image_label(self):
        if not self.current_image_path:
            print("[오류] 현재 표시 중인 이미지가 없습니다.")
            return
        self.save_annotations()
        image_name = os.path.basename(self.current_image_path)
        label_name = os.path.splitext(image_name)[0] + ".txt"
        label_path = os.path.join(self.labels_folder, label_name)
        print(f"[INFO] 라벨 수정 완료: {label_path}")

    def save_annotations(self):
        if not self.current_image_path:
            print("[오류] 이미지가 선택되지 않았습니다.")
            return
        image_name = os.path.basename(self.current_image_path)
        label_name = os.path.splitext(image_name)[0] + ".txt"
        label_path = os.path.join(self.labels_folder, label_name)
        os.makedirs(self.labels_folder, exist_ok=True)
        annotations = []
        for row in range(self.box_table.rowCount()):
            cls_item = self.box_table.item(row, 0)
            x_item = self.box_table.item(row, 1)
            y_item = self.box_table.item(row, 2)
            w_item = self.box_table.item(row, 3)
            h_item = self.box_table.item(row, 4)
            if cls_item and x_item and y_item and w_item and h_item:
                try:
                    cls_idx = int(cls_item.text())
                    x_center = float(x_item.text())
                    y_center = float(y_item.text())
                    w_norm = float(w_item.text())
                    h_norm = float(h_item.text())
                    annotations.append((cls_idx, x_center, y_center, w_norm, h_norm))
                except:
                    continue
        with open(label_path, "w", encoding="utf-8") as f:
            for anno in annotations:
                f.write(f"{anno[0]} {anno[1]:.6f} {anno[2]:.6f} {anno[3]:.6f} {anno[4]:.6f}\n")
        print(f"[INFO] 라벨 저장: {label_path}")

    def delete_selected_box(self):
        selected_items = self.box_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        cls_item = self.box_table.item(row, 0)
        if cls_item:
            data = cls_item.data(Qt.UserRole)
            if data:
                group_item, _ = data
                self.scene.removeItem(group_item)
                self.highlight_box(group_item, False)
        self.box_table.removeRow(row)
        self.resequence_boxes()  ### 박스 삭제 후 순서 업데이트

    def remove_box_from_drawn(self, group_item):
        for i, (g_item, _) in enumerate(self.drawn_boxes):
            if g_item == group_item:
                self.drawn_boxes.pop(i)
                break

    def move_box_up(self):
        selected_items = self.box_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        if row > 0:
            self.swap_table_rows(row, row - 1)
            self.box_table.setCurrentCell(row - 1, 0)
            self.resequence_boxes()

    def move_box_down(self):
        selected_items = self.box_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        if row < self.box_table.rowCount() - 1:
            self.swap_table_rows(row, row + 1)
            self.box_table.setCurrentCell(row + 1, 0)
            self.resequence_boxes()

    def swap_table_rows(self, r1, r2):
        for col in range(self.box_table.columnCount()):
            item1 = self.box_table.takeItem(r1, col)
            item2 = self.box_table.takeItem(r2, col)
            self.box_table.setItem(r1, col, item2)
            self.box_table.setItem(r2, col, item1)

    def set_current_class(self, idx):
        self.current_class_index = idx
        if 0 <= idx < len(self.class_list):
            name = self.class_list[idx]
        else:
            name = "None"
        self.selected_class_label.setText(f"현재 클래스: {name}")

    def on_table_item_changed(self, item):
        if self.iw == 0 or self.ih == 0:
            return
        row = item.row()
        col = item.column()
        if col < 1 or col > 4:
            return
        cls_item = self.box_table.item(row, 0)
        x_item = self.box_table.item(row, 1)
        y_item = self.box_table.item(row, 2)
        w_item = self.box_table.item(row, 3)
        h_item = self.box_table.item(row, 4)
        if not (cls_item and x_item and y_item and w_item and h_item):
            return
        try:
            cls_idx = int(cls_item.text())
            x_center = float(x_item.text())
            y_center = float(y_item.text())
            w_norm = float(w_item.text())
            h_norm = float(h_item.text())
        except:
            return
        w = w_norm * self.iw
        h = h_norm * self.ih
        cx = x_center * self.iw
        cy = y_center * self.ih
        x = cx - w/2
        y = cy - h/2
        data = cls_item.data(Qt.UserRole)
        if data:
            group_item, _ = data
            new_rectF = QRectF(x, y, w, h)
            for child in group_item.childItems():
                if isinstance(child, ResizableRectItem):
                    child.setRect(new_rectF)
            cls_item.setData(Qt.UserRole, (group_item, QRectF(x_center, y_center, w_norm, h_norm)))

    def draw_box_with_label(self, rectF, cls_idx):
        group_item = self.scene.createItemGroup([])
        color_str = self.class_colors[cls_idx % len(self.class_colors)]
        color = QColor(color_str)
        if 0 <= cls_idx < len(self.class_list):
            class_name = self.class_list[cls_idx]
        else:
            class_name = f"{cls_idx}"
        ### 박스 테두리 두께 4
        pen_thickness = 3
        font_size = 20
        box_item = ResizableRectItem(rectF)
        box_item.setPen(QPen(color, pen_thickness))
        box_item.setData(0, cls_idx)
        self.scene.addItem(box_item)
        group_item.addToGroup(box_item)
        ### 클래스 텍스트 (박스 위쪽에 표시)
        class_text = self.scene.addText(f"{cls_idx} {class_name}")
        class_text.setDefaultTextColor(Qt.white)
        fnt = class_text.font()
        fnt.setBold(True)
        fnt.setPointSize(font_size)
        class_text.setFont(fnt)
        label_height = class_text.boundingRect().height()
        class_text.setPos(rectF.x() - 1, rectF.y() - label_height)
        group_item.addToGroup(class_text)
        bg_color = QColor(color)
        bg_color.setAlpha(120)
        label_rect_item = self.scene.addRect(class_text.mapRectToScene(class_text.boundingRect()),
                                               QPen(Qt.NoPen), bg_color)
        group_item.addToGroup(label_rect_item)
        label_rect_item.setZValue(class_text.zValue() - 1)
        ### 시퀀스 번호 텍스트 (폰트 크기 10% 증가, 굵게)
        seq_item = self.scene.addText("1")
        #seq_item.setDefaultTextColor(Qt.red)
        seq_item.setDefaultTextColor(QColor(255, 10, 200))
        seq_font = seq_item.font()
        seq_font.setBold(True)
        seq_font.setPointSize(int(font_size * 1.4))
        seq_item.setFont(seq_font)
        seq_item.setData(1, "sequence")
        ### 시퀀스 번호 위치: 박스 오른쪽 상단에 위치
        seq_item.setPos(rectF.x() + rectF.width() - 40, rectF.y())
        group_item.addToGroup(seq_item)
        return group_item

    def add_box_to_table(self, cls_idx, rect_norm, group_item):
        row = self.box_table.rowCount()
        self.box_table.insertRow(row)
        cls_item = QTableWidgetItem(str(cls_idx))
        cls_item.setData(Qt.UserRole, (group_item, rect_norm))
        x_center = rect_norm.x()
        y_center = rect_norm.y()
        w_norm = rect_norm.width()
        h_norm = rect_norm.height()
        self.box_table.setItem(row, 0, cls_item)
        self.box_table.setItem(row, 1, QTableWidgetItem(f"{x_center:.6f}"))
        self.box_table.setItem(row, 2, QTableWidgetItem(f"{y_center:.6f}"))
        self.box_table.setItem(row, 3, QTableWidgetItem(f"{w_norm:.6f}"))
        self.box_table.setItem(row, 4, QTableWidgetItem(f"{h_norm:.6f}"))

    def resequence_boxes(self):
        for row in range(self.box_table.rowCount()):
            cls_item = self.box_table.item(row, 0)
            if cls_item:
                data = cls_item.data(Qt.UserRole)
                if data:
                    group_item, rect_norm = data
                    seq_num = row + 1
                    for child in group_item.childItems():
                        if hasattr(child, "data") and child.data(1) == "sequence":
                            child.setPlainText(str(seq_num))
                            x_center = float(self.box_table.item(row, 1).text()) * self.iw
                            y_center = float(self.box_table.item(row, 2).text()) * self.ih
                            w = float(self.box_table.item(row, 3).text()) * self.iw
                            h = float(self.box_table.item(row, 4).text()) * self.ih
                            seq_x = x_center + w/2 - 40
                            seq_y = y_center + h/2 - 40
                            child.setPos(seq_x, seq_y)
                            break

    def eventFilter(self, source, event):
        if source == self.box_table and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                self.keyPressEvent(event)
                return True
        if source is self.view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                self.start_point = self.view.mapToScene(event.pos())
                self.is_drawing = True
                self.drawing_box = QGraphicsRectItem()
                self.drawing_box.setPen(QPen(Qt.red, 2))
                self.scene.addItem(self.drawing_box)
                return True
            elif event.type() == QEvent.MouseMove and self.is_drawing and self.drawing_box:
                end_point = self.view.mapToScene(event.pos())
                rect = QRectF(self.start_point, end_point).normalized()
                w = rect.width()
                h = rect.height()
                cx = rect.center().x()
                cy = rect.center().y()
                w = max(1, w)
                h = max(1, h)
                w = min(w, self.iw)
                h = min(h, self.ih)
                min_x_center = w / 2
                max_x_center = self.iw - w / 2
                min_y_center = h / 2
                max_y_center = self.ih - h / 2
                if min_x_center > max_x_center:
                    w = self.iw
                    cx = self.iw / 2
                else:
                    cx = max(min_x_center, min(cx, max_x_center))
                if min_y_center > max_y_center:
                    h = self.ih
                    cy = self.ih / 2
                else:
                    cy = max(min_y_center, min(cy, max_y_center))
                x = cx - w/2
                y = cy - h/2
                clamped_rect = QRectF(x, y, w, h)
                self.drawing_box.setRect(clamped_rect)
                return True
            elif event.type() == QEvent.MouseButtonRelease and self.is_drawing and self.drawing_box:
                self.is_drawing = False
                rect = self.drawing_box.rect()
                self.scene.removeItem(self.drawing_box)
                if rect.width() >= 5 and rect.height() >= 5:
                    x_center_norm = (rect.x() + rect.width()/2) / self.iw
                    y_center_norm = (rect.y() + rect.height()/2) / self.ih
                    w_norm = rect.width() / self.iw
                    h_norm = rect.height() / self.ih
                    self.add_box(QRectF(x_center_norm, y_center_norm, w_norm, h_norm), self.current_class_index)
                self.drawing_box = None
                return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        try:
            if event.key() == Qt.Key_S:
                self.save_annotations()
                event.accept()
            elif Qt.Key_0 <= event.key() <= Qt.Key_9:
                idx = event.key() - Qt.Key_0
                if 0 <= idx < len(self.class_list):
                    self.set_current_class(idx)
                event.accept()
            elif event.key() == Qt.Key_D:
                if self.drawn_boxes:
                    g_item, _ = self.drawn_boxes.pop()
                    self.delete_box_by_group_item(g_item)
                event.accept()
            elif event.key() == Qt.Key_M:
                self.copy_current_image_label()
                event.accept()
            elif event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                if event.key() == Qt.Key_Left:
                    self.previous_image()
                elif event.key() == Qt.Key_Right:
                    self.next_image()
                elif event.key() == Qt.Key_Up:
                    self.previous_image()
                elif event.key() == Qt.Key_Down:
                    self.next_image()
                event.accept()
            else:
                super().keyPressEvent(event)
        except Exception as e:
            pass

    def delete_box_by_group_item(self, group_item):
        for row in range(self.box_table.rowCount()):
            cls_item = self.box_table.item(row, 0)
            if cls_item:
                data = cls_item.data(Qt.UserRole)
                if data:
                    g_item, _ = data
                    if g_item == group_item:
                        self.scene.removeItem(group_item)
                        self.box_table.removeRow(row)
                        self.highlight_box(group_item, False)
                        self.resequence_boxes()
                        break

###################################################################################################
###################################################################################################

def main(opt):
    app = QApplication(sys.argv)
    window = ImageLabelAnnotator(opt)
    window.show()
    sys.exit(app.exec_())

###################################################################################################
###################################################################################################

if __name__ == "__main__":
    opt = parse_opt()
    main(opt)

###################################################################################################
###################################################################################################