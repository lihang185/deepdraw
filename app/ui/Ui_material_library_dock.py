# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'material_library_dock.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_MaterialLibraryDock(object):
    def setupUi(self, assetLibrary):
        if not assetLibrary.objectName():
            assetLibrary.setObjectName(u"assetLibrary")
        assetLibrary.setMinimumSize(QSize(300, 0))
        assetLibrary.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(assetLibrary.sizePolicy().hasHeightForWidth())
        assetLibrary.setSizePolicy(sizePolicy)
        self.dockContents = QWidget()
        self.dockContents.setObjectName(u"dockContents")
        self.dockContents.setMinimumSize(QSize(0, 0))
        self.dockContents.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy.setHeightForWidth(self.dockContents.sizePolicy().hasHeightForWidth())
        self.dockContents.setSizePolicy(sizePolicy)
        self.contentLayout = QVBoxLayout(self.dockContents)
        self.contentLayout.setSpacing(6)
        self.contentLayout.setObjectName(u"contentLayout")
        self.contentLayout.setContentsMargins(6, 9, 6, 9)
        self.material_parameters = QGroupBox(self.dockContents)
        self.material_parameters.setObjectName(u"material_parameters")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.material_parameters.sizePolicy().hasHeightForWidth())
        self.material_parameters.setSizePolicy(sizePolicy1)
        self.materialParametersLayout = QFormLayout(self.material_parameters)
        self.materialParametersLayout.setObjectName(u"materialParametersLayout")
        self.material_texture_preview = QLabel(self.material_parameters)
        self.material_texture_preview.setObjectName(u"material_texture_preview")
        self.material_texture_preview.setMinimumSize(QSize(0, 150))
        self.material_texture_preview.setMaximumSize(QSize(16777215, 150))
        self.material_texture_preview.setAlignment(Qt.AlignCenter)

        self.materialParametersLayout.setWidget(0, QFormLayout.SpanningRole, self.material_texture_preview)

        self.color_label = QLabel(self.material_parameters)
        self.color_label.setObjectName(u"color_label")

        self.materialParametersLayout.setWidget(2, QFormLayout.LabelRole, self.color_label)

        self.material_color = QPushButton(self.material_parameters)
        self.material_color.setObjectName(u"material_color")
        self.material_color.setMinimumSize(QSize(0, 24))

        self.materialParametersLayout.setWidget(2, QFormLayout.FieldRole, self.material_color)

        self.texture_label = QLabel(self.material_parameters)
        self.texture_label.setObjectName(u"texture_label")

        self.materialParametersLayout.setWidget(3, QFormLayout.LabelRole, self.texture_label)

        self.textureLayout = QHBoxLayout()
        self.textureLayout.setObjectName(u"textureLayout")
        self.material_texture = QLineEdit(self.material_parameters)
        self.material_texture.setObjectName(u"material_texture")
        self.material_texture.setReadOnly(True)

        self.textureLayout.addWidget(self.material_texture)

        self.material_texture_choose = QToolButton(self.material_parameters)
        self.material_texture_choose.setObjectName(u"material_texture_choose")

        self.textureLayout.addWidget(self.material_texture_choose)


        self.materialParametersLayout.setLayout(3, QFormLayout.FieldRole, self.textureLayout)

        self.size_u_label = QLabel(self.material_parameters)
        self.size_u_label.setObjectName(u"size_u_label")

        self.materialParametersLayout.setWidget(4, QFormLayout.LabelRole, self.size_u_label)

        self.textureSizeLayout = QHBoxLayout()
        self.textureSizeLayout.setObjectName(u"textureSizeLayout")
        self.material_size_u = QDoubleSpinBox(self.material_parameters)
        self.material_size_u.setObjectName(u"material_size_u")
        self.material_size_u.setDecimals(3)
        self.material_size_u.setMinimum(0.001000000000000)
        self.material_size_u.setMaximum(1000000.000000000000000)
        self.material_size_u.setValue(100.000000000000000)
        self.material_size_u.setKeyboardTracking(False)

        self.textureSizeLayout.addWidget(self.material_size_u)

        self.texture_size_separator = QLabel(self.material_parameters)
        self.texture_size_separator.setObjectName(u"texture_size_separator")

        self.textureSizeLayout.addWidget(self.texture_size_separator)

        self.material_size_v = QDoubleSpinBox(self.material_parameters)
        self.material_size_v.setObjectName(u"material_size_v")
        self.material_size_v.setDecimals(3)
        self.material_size_v.setMinimum(0.001000000000000)
        self.material_size_v.setMaximum(1000000.000000000000000)
        self.material_size_v.setValue(100.000000000000000)
        self.material_size_v.setKeyboardTracking(False)

        self.textureSizeLayout.addWidget(self.material_size_v)

        self.texture_size_unit = QLabel(self.material_parameters)
        self.texture_size_unit.setObjectName(u"texture_size_unit")

        self.textureSizeLayout.addWidget(self.texture_size_unit)


        self.materialParametersLayout.setLayout(4, QFormLayout.FieldRole, self.textureSizeLayout)

        self.opacity_label = QLabel(self.material_parameters)
        self.opacity_label.setObjectName(u"opacity_label")

        self.materialParametersLayout.setWidget(5, QFormLayout.LabelRole, self.opacity_label)

        self.opacityLayout = QHBoxLayout()
        self.opacityLayout.setObjectName(u"opacityLayout")
        self.material_use_opacity = QCheckBox(self.material_parameters)
        self.material_use_opacity.setObjectName(u"material_use_opacity")

        self.opacityLayout.addWidget(self.material_use_opacity)

        self.material_opacity = QSlider(self.material_parameters)
        self.material_opacity.setObjectName(u"material_opacity")
        self.material_opacity.setOrientation(Qt.Horizontal)
        self.material_opacity.setMaximum(100)

        self.opacityLayout.addWidget(self.material_opacity)

        self.material_opacity_value = QLabel(self.material_parameters)
        self.material_opacity_value.setObjectName(u"material_opacity_value")

        self.opacityLayout.addWidget(self.material_opacity_value)


        self.materialParametersLayout.setLayout(5, QFormLayout.FieldRole, self.opacityLayout)

        self.line_color_label = QLabel(self.material_parameters)
        self.line_color_label.setObjectName(u"line_color_label")

        self.materialParametersLayout.setWidget(6, QFormLayout.LabelRole, self.line_color_label)

        self.lineColorLayout = QHBoxLayout()
        self.lineColorLayout.setObjectName(u"lineColorLayout")
        self.material_use_line_color = QCheckBox(self.material_parameters)
        self.material_use_line_color.setObjectName(u"material_use_line_color")

        self.lineColorLayout.addWidget(self.material_use_line_color)

        self.material_line_color = QPushButton(self.material_parameters)
        self.material_line_color.setObjectName(u"material_line_color")

        self.lineColorLayout.addWidget(self.material_line_color)


        self.materialParametersLayout.setLayout(6, QFormLayout.FieldRole, self.lineColorLayout)

        self.material_name_label = QLabel(self.material_parameters)
        self.material_name_label.setObjectName(u"material_name_label")

        self.materialParametersLayout.setWidget(1, QFormLayout.LabelRole, self.material_name_label)

        self.material_name = QLineEdit(self.material_parameters)
        self.material_name.setObjectName(u"material_name")

        self.materialParametersLayout.setWidget(1, QFormLayout.FieldRole, self.material_name)


        self.contentLayout.addWidget(self.material_parameters)

        self.catalogActionsLayout = QHBoxLayout()
        self.catalogActionsLayout.setSpacing(6)
        self.catalogActionsLayout.setObjectName(u"catalogActionsLayout")
        self.catalogActionsLayout.setContentsMargins(0, 0, 0, 0)
        self.folder_button = QPushButton(self.dockContents)
        self.folder_button.setObjectName(u"folder_button")
        self.folder_button.setMinimumSize(QSize(0, 0))
        self.folder_button.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy2 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.folder_button.sizePolicy().hasHeightForWidth())
        self.folder_button.setSizePolicy(sizePolicy2)
        self.folder_button.setCheckable(False)
        self.folder_button.setChecked(False)

        self.catalogActionsLayout.addWidget(self.folder_button)

        self.refresh_button = QPushButton(self.dockContents)
        self.refresh_button.setObjectName(u"refresh_button")
        self.refresh_button.setMinimumSize(QSize(0, 0))
        self.refresh_button.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy2.setHeightForWidth(self.refresh_button.sizePolicy().hasHeightForWidth())
        self.refresh_button.setSizePolicy(sizePolicy2)
        self.refresh_button.setCheckable(False)
        self.refresh_button.setChecked(False)

        self.catalogActionsLayout.addWidget(self.refresh_button)

        self.apply = QPushButton(self.dockContents)
        self.apply.setObjectName(u"apply")
        self.apply.setMinimumSize(QSize(0, 0))
        self.apply.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy2.setHeightForWidth(self.apply.sizePolicy().hasHeightForWidth())
        self.apply.setSizePolicy(sizePolicy2)
        self.apply.setCheckable(False)
        self.apply.setChecked(False)
        self.apply.setEnabled(False)

        self.catalogActionsLayout.addWidget(self.apply)

        self.new_material = QPushButton(self.dockContents)
        self.new_material.setObjectName(u"new_material")

        self.catalogActionsLayout.addWidget(self.new_material)


        self.contentLayout.addLayout(self.catalogActionsLayout)

        self.items = QListWidget(self.dockContents)
        self.items.setObjectName(u"items")
        self.items.setMinimumSize(QSize(0, 0))
        self.items.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.items.sizePolicy().hasHeightForWidth())
        self.items.setSizePolicy(sizePolicy3)
        self.items.setViewMode(QListView.IconMode)
        self.items.setResizeMode(QListView.Adjust)
        self.items.setMovement(QListView.Static)
        self.items.setIconSize(QSize(72, 72))
        self.items.setGridSize(QSize(88, 106))
        self.items.setWordWrap(True)
        self.items.setSpacing(0)
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.contentLayout.addWidget(self.items)

        self.profileActionsLayout = QHBoxLayout()
        self.profileActionsLayout.setSpacing(6)
        self.profileActionsLayout.setObjectName(u"profileActionsLayout")
        self.profileActionsLayout.setContentsMargins(0, 0, 0, 0)

        self.contentLayout.addLayout(self.profileActionsLayout)

        self.message = QLabel(self.dockContents)
        self.message.setObjectName(u"message")
        self.message.setMinimumSize(QSize(0, 0))
        self.message.setMaximumSize(QSize(16777215, 16777215))
        sizePolicy4 = QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.message.sizePolicy().hasHeightForWidth())
        self.message.setSizePolicy(sizePolicy4)
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.message.setTextFormat(Qt.PlainText)

        self.contentLayout.addWidget(self.message)

        self.contentLayout.setStretch(2, 1)
        assetLibrary.setWidget(self.dockContents)

        self.retranslateUi(assetLibrary)

        QMetaObject.connectSlotsByName(assetLibrary)
    # setupUi

    def retranslateUi(self, assetLibrary):
#if QT_CONFIG(tooltip)
        assetLibrary.setToolTip("")
#endif // QT_CONFIG(tooltip)
        assetLibrary.setStyleSheet("")
        assetLibrary.setWindowTitle(QCoreApplication.translate("MaterialLibraryDock", u"\u6a21\u578b\u5e93", None))
#if QT_CONFIG(tooltip)
        self.dockContents.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.dockContents.setStyleSheet("")
        self.material_parameters.setTitle(QCoreApplication.translate("MaterialLibraryDock", u"\u6750\u8d28\u53c2\u6570", None))
        self.material_texture_preview.setText("")
        self.color_label.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u989c\u8272", None))
        self.material_color.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u672a\u9009\u62e9\u6750\u8d28", None))
        self.texture_label.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u8d34\u56fe", None))
        self.material_texture.setPlaceholderText(QCoreApplication.translate("MaterialLibraryDock", u"\u672a\u9009\u62e9\u6750\u8d28", None))
#if QT_CONFIG(tooltip)
        self.material_texture_choose.setToolTip(QCoreApplication.translate("MaterialLibraryDock", u"\u9009\u62e9\u8d34\u56fe", None))
#endif // QT_CONFIG(tooltip)
        self.material_texture_choose.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u2026", None))
        self.size_u_label.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u8d34\u56fe\u5c3a\u5bf8", None))
#if QT_CONFIG(tooltip)
        self.material_size_u.setToolTip(QCoreApplication.translate("MaterialLibraryDock", u"U \u65b9\u5411\u5c3a\u5bf8\uff08cm\uff09", None))
#endif // QT_CONFIG(tooltip)
        self.texture_size_separator.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u00d7", None))
#if QT_CONFIG(tooltip)
        self.material_size_v.setToolTip(QCoreApplication.translate("MaterialLibraryDock", u"V \u65b9\u5411\u5c3a\u5bf8\uff08cm\uff09", None))
#endif // QT_CONFIG(tooltip)
        self.texture_size_unit.setText(QCoreApplication.translate("MaterialLibraryDock", u"cm", None))
        self.opacity_label.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u900f\u660e\u5ea6", None))
#if QT_CONFIG(tooltip)
        self.material_use_opacity.setToolTip(QCoreApplication.translate("MaterialLibraryDock", u"\u542f\u7528\u900f\u660e\u6750\u8d28", None))
#endif // QT_CONFIG(tooltip)
        self.material_opacity_value.setText(QCoreApplication.translate("MaterialLibraryDock", u"1.00", None))
        self.line_color_label.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u7ebf\u6bb5\u989c\u8272", None))
#if QT_CONFIG(tooltip)
        self.material_use_line_color.setToolTip(QCoreApplication.translate("MaterialLibraryDock", u"\u81ea\u5b9a\u4e49\u7ebf\u6bb5\u989c\u8272", None))
#endif // QT_CONFIG(tooltip)
        self.material_line_color.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u9009\u62e9\u989c\u8272", None))
        self.material_name_label.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u6750\u8d28\u540d", None))
#if QT_CONFIG(tooltip)
        self.folder_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.folder_button.setStyleSheet("")
        self.folder_button.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u6dfb\u52a0\u76ee\u5f55", None))
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setStyleSheet("")
        self.refresh_button.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u5237\u65b0", None))
#if QT_CONFIG(tooltip)
        self.apply.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.apply.setStyleSheet("")
        self.apply.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u63d2\u5165\u573a\u666f", None))
        self.new_material.setText(QCoreApplication.translate("MaterialLibraryDock", u"\u65b0\u5efa\u6750\u8d28", None))
#if QT_CONFIG(tooltip)
        self.items.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.items.setStyleSheet("")
#if QT_CONFIG(tooltip)
        self.message.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.message.setStyleSheet("")
        self.message.setText("")
    # retranslateUi

