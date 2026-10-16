# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'object_properties_dialog.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_ObjectPropertiesDialog(object):
    def setupUi(self, ObjectPropertiesDialog):
        if not ObjectPropertiesDialog.objectName():
            ObjectPropertiesDialog.setObjectName(u"ObjectPropertiesDialog")
        ObjectPropertiesDialog.resize(640, 480)
        self.contentLayout = QVBoxLayout(ObjectPropertiesDialog)
        self.contentLayout.setObjectName(u"contentLayout")
        self.properties_text = QPlainTextEdit(ObjectPropertiesDialog)
        self.properties_text.setObjectName(u"properties_text")
        self.properties_text.setReadOnly(True)
        self.properties_text.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.contentLayout.addWidget(self.properties_text)

        self.buttons = QDialogButtonBox(ObjectPropertiesDialog)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.Close)

        self.contentLayout.addWidget(self.buttons)


        self.retranslateUi(ObjectPropertiesDialog)

        QMetaObject.connectSlotsByName(ObjectPropertiesDialog)
    # setupUi

    def retranslateUi(self, ObjectPropertiesDialog):
        ObjectPropertiesDialog.setWindowTitle(QCoreApplication.translate("ObjectPropertiesDialog", u"\u5bf9\u8c61\u5c5e\u6027", None))
    # retranslateUi

