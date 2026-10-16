# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'text_dialog.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_TextDialog(object):
    def setupUi(self, TextDialog):
        if not TextDialog.objectName():
            TextDialog.setObjectName(u"TextDialog")
        TextDialog.resize(347, 339)
        self.layout = QVBoxLayout(TextDialog)
        self.layout.setObjectName(u"layout")
        self.textInput = QPlainTextEdit(TextDialog)
        self.textInput.setObjectName(u"textInput")

        self.layout.addWidget(self.textInput)

        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.fontLabel = QLabel(TextDialog)
        self.fontLabel.setObjectName(u"fontLabel")

        self.form.setWidget(0, QFormLayout.LabelRole, self.fontLabel)

        self.fontInput = QFontComboBox(TextDialog)
        self.fontInput.setObjectName(u"fontInput")

        self.form.setWidget(0, QFormLayout.FieldRole, self.fontInput)

        self.heightLabel = QLabel(TextDialog)
        self.heightLabel.setObjectName(u"heightLabel")

        self.form.setWidget(1, QFormLayout.LabelRole, self.heightLabel)

        self.heightInput = QDoubleSpinBox(TextDialog)
        self.heightInput.setObjectName(u"heightInput")
        self.heightInput.setDecimals(0)
        self.heightInput.setMinimum(0.000000000000000)
        self.heightInput.setMaximum(10000.000000000000000)
        self.heightInput.setSingleStep(5.000000000000000)
        self.heightInput.setValue(100.000000000000000)

        self.form.setWidget(1, QFormLayout.FieldRole, self.heightInput)

        self.extrudeInput = QCheckBox(TextDialog)
        self.extrudeInput.setObjectName(u"extrudeInput")
        self.extrudeInput.setChecked(True)

        self.form.setWidget(2, QFormLayout.LabelRole, self.extrudeInput)

        self.depthInput = QDoubleSpinBox(TextDialog)
        self.depthInput.setObjectName(u"depthInput")
        self.depthInput.setDecimals(0)
        self.depthInput.setMinimum(0.000000000000000)
        self.depthInput.setMaximum(10000.000000000000000)
        self.depthInput.setValue(20.000000000000000)

        self.form.setWidget(2, QFormLayout.FieldRole, self.depthInput)

        self.errorControlLabel = QLabel(TextDialog)
        self.errorControlLabel.setObjectName(u"errorControlLabel")

        self.form.setWidget(3, QFormLayout.LabelRole, self.errorControlLabel)

        self.errorInput = QDoubleSpinBox(TextDialog)
        self.errorInput.setObjectName(u"errorInput")
        self.errorInput.setDecimals(2)
        self.errorInput.setMinimum(0.000000000000000)
        self.errorInput.setMaximum(5.000000000000000)
        self.errorInput.setSingleStep(0.050000000000000)
        self.errorInput.setValue(0.300000000000000)

        self.form.setWidget(3, QFormLayout.FieldRole, self.errorInput)


        self.layout.addLayout(self.form)

        self.errorLabel = QLabel(TextDialog)
        self.errorLabel.setObjectName(u"errorLabel")
        self.errorLabel.setWordWrap(True)

        self.layout.addWidget(self.errorLabel)

        self.buttons = QDialogButtonBox(TextDialog)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.layout.addWidget(self.buttons)


        self.retranslateUi(TextDialog)

        QMetaObject.connectSlotsByName(TextDialog)
    # setupUi

    def retranslateUi(self, TextDialog):
        TextDialog.setWindowTitle(QCoreApplication.translate("TextDialog", u"3D \u6587\u5b57", None))
        self.textInput.setPlaceholderText(QCoreApplication.translate("TextDialog", u"\u8f93\u5165\u6587\u5b57\uff0c\u652f\u6301\u6362\u884c", None))
        self.fontLabel.setText(QCoreApplication.translate("TextDialog", u"\u5b57\u4f53", None))
        self.heightLabel.setText(QCoreApplication.translate("TextDialog", u"\u6587\u5b57\u9ad8\u5ea6\uff08cm\uff09", None))
        self.extrudeInput.setText(QCoreApplication.translate("TextDialog", u"\u6324\u51fa\u5b9e\u4f53", None))
        self.depthInput.setPrefix("")
        self.depthInput.setSuffix("")
        self.errorControlLabel.setText(QCoreApplication.translate("TextDialog", u"\u8bef\u5dee\u63a7\u5236", None))
#if QT_CONFIG(tooltip)
        self.errorInput.setToolTip(QCoreApplication.translate("TextDialog", u"\u76f8\u5bf9\u6587\u5b57\u9ad8\u5ea6\u7684\u66f2\u7ebf\u8fd1\u4f3c\u8bef\u5dee\uff1b\u503c\u8d8a\u5927\uff0c\u5206\u6bb5\u8d8a\u5c11", None))
#endif // QT_CONFIG(tooltip)
        self.errorInput.setSuffix(QCoreApplication.translate("TextDialog", u" %", None))
        self.errorLabel.setText("")
    # retranslateUi

