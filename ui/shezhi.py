from ui.ui_shezhi import *
from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Qt
from core.settings import current_theme, clear_settings_file


class Shezhi(QWidget, Ui_shezhi):
    def __init__(self, parent, fs):
        super(Shezhi, self).__init__(parent)
        del fs  # 设置页不直接使用共享 fs
        self.setupUi(self)
        self.parent = parent
        # Aplicación en español únicamente: se oculta el selector de idioma.
        if hasattr(self, "groupBox_2"):
            self.groupBox_2.hide()
        # 根据当前主题预选单选按钮（默认浅色）
        if current_theme() == "dark":
            self.shezhi_shense.setChecked(True)
        else:
            self.shezhi_qianse.setChecked(True)
        # 恢复上次存档过滤设置（首次使用时所有项全勾选）
        saved = getattr(self.parent, 'save_filters', None)
        if saved is not None:
            self._apply_saved_filters(saved)
        self.shezhi_yingyong.clicked.connect(self.on_apply)
        self.shezhi_qingchu.clicked.connect(self.on_clear_settings)

    def _apply_saved_filters(self, saved):
        """将已保存的过滤设置还原到 QListWidget 的勾选状态。"""
        mapping = [
            (0, "fs"), (1, "eqs"), (2, "rels"),
            (3, "vs"), (4, "cache"), (5, "pjs"),
            (6, "ljs"), (7, "blockly"), (8, "texts"),
            (9, "combos"), (10, "views"), (11, "save_settings"),
        ]
        # 先全部取消，再按要求勾选
        for i in range(self.shezhi_cundang.count()):
            self.shezhi_cundang.item(i).setCheckState(Qt.Unchecked)
        for idx, key in mapping:
            if saved.get(key, True):
                self.shezhi_cundang.item(idx).setCheckState(Qt.Checked)

    def on_apply(self):
        # Idioma fijo en español (ya no hay selección de idioma).
        lang = "es_ES"
        # 主题切换
        theme = "dark" if self.shezhi_shense.isChecked() else "light"
        if self.parent is not None:
            if hasattr(self.parent, "change_language"):
                self.parent.change_language(lang)
            if theme == "dark":
                self.parent.dark()
            else:
                self.parent.light()
        from core.settings import save_theme
        save_theme(theme)

        # 存档设置：将勾选状态写入 MainWindow.save_filters，
        # 供 saves.py 存档/读档时决定哪些数据类别生效
        def _checked(idx):
            it = self.shezhi_cundang.item(idx)
            return it is not None and it.checkState() == Qt.Checked

        self.parent.save_filters = {
            "fs":            _checked(0),   # 函数列表
            "eqs":           _checked(1),   # 方程列表（方程组）
            "rels":          _checked(2),   # 不等式列表（不等式组）
            "vs":            _checked(3),   # 向量列表
            "cache":         _checked(4),   # 所有缓存区内容
            "pjs":           _checked(5),   # 平面几何对象列表
            "ljs":           _checked(6),   # 立体几何对象列表
            "blockly":       _checked(7),   # 积木编辑区工程
            "texts":         _checked(8),   # 所有文本框文本
            "combos":        _checked(9),   # 所有选择框选项
            "views":         _checked(10),  # 所有表达式显示框内容
            "save_settings": _checked(11),  # 所有设置选项
        }

    def on_clear_settings(self):
        """Borra el archivo de configuración: avisa, confirma dos veces y restaura
        los valores por defecto."""

        # Primera: advertencia de operación destructiva
        first = QMessageBox.warning(
            self,
            "Borrar archivo de configuración",
            "Esta operación elimina el archivo de configuración (idioma, tema, filtros "
            "de guardado y todas las preferencias) y no se puede deshacer.\n¿Desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if first != QMessageBox.StandardButton.Yes:
            return

        # Segunda: confirmación adicional
        second = QMessageBox.question(
            self,
            "Confirmar de nuevo",
            "Confirme de nuevo: ¿realmente desea borrar toda la configuración y restaurar los valores por defecto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if second != QMessageBox.StandardButton.Yes:
            return

        # 先应用默认界面（语言 + 主题），这会因保存而重新写入设置文件
        if self.parent is not None and hasattr(self.parent, "change_language"):
            self.parent.change_language("es_ES")  # idioma único: español
            self.parent.light()
        # 删除刚写入的设置文件，达到“清除”效果
        clear_settings_file()

        # Sincroniza los botones de esta página con los valores por defecto (tema claro)
        self.shezhi_shense.setChecked(False)
        self.shezhi_qianse.setChecked(True)

        QMessageBox.information(
            self,
            "Listo",
            "Se borró el archivo de configuración y se restauraron los valores por "
            "defecto (reinicie el programa para que surta pleno efecto).",
        )
