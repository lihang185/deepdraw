# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_browser.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from  . import resources_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(350, 600)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(0, 0))
        Form.setMaximumSize(QSize(16777215, 16777215))
        self.verticalLayout_3 = QVBoxLayout(Form)
        self.verticalLayout_3.setSpacing(5)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(1, 1, 1, 1)
        self.horizontalLayout_1 = QHBoxLayout()
        self.horizontalLayout_1.setSpacing(3)
        self.horizontalLayout_1.setObjectName(u"horizontalLayout_1")
        self.comPaint = QLabel(Form)
        self.comPaint.setObjectName(u"comPaint")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.comPaint.sizePolicy().hasHeightForWidth())
        self.comPaint.setSizePolicy(sizePolicy1)
        self.comPaint.setMinimumSize(QSize(100, 100))
        self.comPaint.setMaximumSize(QSize(100, 100))
        self.comPaint.setAutoFillBackground(False)
        self.comPaint.setStyleSheet(u"QLabel {border: 1px solid rgba(200, 200, 200, 150); background-color: rgba(0, 0, 0, 0); border-radius: 4px;}")
        self.comPaint.setScaledContents(False)
        self.comPaint.setAlignment(Qt.AlignCenter)
        self.comPaint.setWordWrap(False)

        self.horizontalLayout_1.addWidget(self.comPaint)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.comName = QLineEdit(Form)
        self.comName.setObjectName(u"comName")
        self.comName.setMinimumSize(QSize(0, 25))
        self.comName.setMaximumSize(QSize(16777215, 25))
        self.comName.setReadOnly(False)

        self.verticalLayout.addWidget(self.comName)

        self.comDescription = QTextEdit(Form)
        self.comDescription.setObjectName(u"comDescription")
        sizePolicy2 = QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.comDescription.sizePolicy().hasHeightForWidth())
        self.comDescription.setSizePolicy(sizePolicy2)
        self.comDescription.setMinimumSize(QSize(0, 68))
        self.comDescription.setMaximumSize(QSize(16777215, 68))

        self.verticalLayout.addWidget(self.comDescription)


        self.horizontalLayout_1.addLayout(self.verticalLayout)


        self.verticalLayout_3.addLayout(self.horizontalLayout_1)

        self.tabWidget = QTabWidget(Form)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_2 = QVBoxLayout(self.tab)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(1, 1, 1, 1)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.comSelect = QComboBox(self.tab)
        self.comSelect.setObjectName(u"comSelect")
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy3.setHorizontalStretch(255)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.comSelect.sizePolicy().hasHeightForWidth())
        self.comSelect.setSizePolicy(sizePolicy3)
        self.comSelect.setMaximumSize(QSize(16777215, 16777215))

        self.horizontalLayout_2.addWidget(self.comSelect)

        self.comDetails = QToolButton(self.tab)
        self.comDetails.setObjectName(u"comDetails")
        self.comDetails.setStyleSheet(u"QToolButton { border: none; background: transparent; border-radius: 4px;}\n"
"QToolButton:hover { background-color: rgba(0, 120, 215, 60); }\n"
"QToolButton:pressed { background-color: rgba(0, 120, 215, 80); }\n"
"QToolButton:checked { background-color: rgba(0, 120, 215, 100); border: 1px solid rgba(0, 120, 215, 150); }")
        icon = QIcon()
        icon.addFile(u":/toolbar/icons/tb_layer_manager.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.comDetails.setIcon(icon)
        self.comDetails.setIconSize(QSize(22, 22))
        self.comDetails.setCheckable(True)

        self.horizontalLayout_2.addWidget(self.comDetails)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.comLists = QListWidget(self.tab)
        self.comLists.setObjectName(u"comLists")
        self.comLists.setIconSize(QSize(64, 64))
        self.comLists.setViewMode(QListView.ListMode)

        self.verticalLayout_2.addWidget(self.comLists)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.tabWidget.addTab(self.tab_2, "")

        self.verticalLayout_3.addWidget(self.tabWidget)


        self.retranslateUi(Form)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.comPaint.setText("")
        self.comDescription.setHtml(QCoreApplication.translate("Form", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'SimSun'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
        self.comDetails.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("Form", u"\u9009\u62e9", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("Form", u"\u7f16\u8f91", None))
    # retranslateUi

