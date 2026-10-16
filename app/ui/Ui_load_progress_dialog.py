# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'load_progress_dialog.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_LoadProgressDialog(object):
    def setupUi(self, LoadProgressDialog):
        if not LoadProgressDialog.objectName():
            LoadProgressDialog.setObjectName(u"LoadProgressDialog")
        LoadProgressDialog.setMinimumSize(QSize(400, 110))
        self.verticalLayout = QVBoxLayout(LoadProgressDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.status_label = QLabel(LoadProgressDialog)
        self.status_label.setObjectName(u"status_label")

        self.verticalLayout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(LoadProgressDialog)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.verticalLayout.addWidget(self.progress_bar)

        self.detail_label = QLabel(LoadProgressDialog)
        self.detail_label.setObjectName(u"detail_label")

        self.verticalLayout.addWidget(self.detail_label)

        self.choice_label = QLabel(LoadProgressDialog)
        self.choice_label.setObjectName(u"choice_label")
        self.choice_label.setWordWrap(True)

        self.verticalLayout.addWidget(self.choice_label)

        self.choice_buttons = QWidget(LoadProgressDialog)
        self.choice_buttons.setObjectName(u"choice_buttons")
        self.buttonLayout = QHBoxLayout(self.choice_buttons)
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.buttonLayout.addItem(self.buttonSpacer)

        self.initialize_button = QPushButton(self.choice_buttons)
        self.initialize_button.setObjectName(u"initialize_button")

        self.buttonLayout.addWidget(self.initialize_button)

        self.skip_button = QPushButton(self.choice_buttons)
        self.skip_button.setObjectName(u"skip_button")

        self.buttonLayout.addWidget(self.skip_button)


        self.verticalLayout.addWidget(self.choice_buttons)


        self.retranslateUi(LoadProgressDialog)

        self.initialize_button.setDefault(True)


        QMetaObject.connectSlotsByName(LoadProgressDialog)
    # setupUi

    def retranslateUi(self, LoadProgressDialog):
        LoadProgressDialog.setWindowTitle(QCoreApplication.translate("LoadProgressDialog", u"\u6253\u5f00\u6a21\u578b", None))
        self.status_label.setText(QCoreApplication.translate("LoadProgressDialog", u"\u6b63\u5728\u8bfb\u53d6\u6a21\u578b\u2026\u2026", None))
        self.detail_label.setText("")
        self.choice_label.setText(QCoreApplication.translate("LoadProgressDialog", u"\u6a21\u578b\u975e\u5e38\u5927\u3002\u662f\u5426\u63d0\u524d\u521d\u59cb\u5316\u6a21\u578b\u6570\u636e\uff1f\n"
"\u51cf\u5c11\u6d4f\u89c8\u573a\u666f\u65f6\u7684\u505c\u987f\uff1b\u521d\u59cb\u5316\u53ef\u80fd\u9700\u8981\u4e00\u4e9b\u65f6\u95f4\u3002", None))
        self.initialize_button.setText(QCoreApplication.translate("LoadProgressDialog", u"\u521d\u59cb\u5316", None))
        self.skip_button.setText(QCoreApplication.translate("LoadProgressDialog", u"\u8df3\u8fc7", None))
    # retranslateUi

