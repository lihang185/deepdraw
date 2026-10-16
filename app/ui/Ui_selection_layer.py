# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'selection_layer.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_SelectionLayer(object):
    def setupUi(self, SelectionLayer):
        if not SelectionLayer.objectName():
            SelectionLayer.setObjectName(u"SelectionLayer")
        self.layout = QHBoxLayout(SelectionLayer)
        self.layout.setObjectName(u"layout")
        self.layout.setContentsMargins(4, 0, 4, 0)
        self.layerCombo = QComboBox(SelectionLayer)
        self.layerCombo.setObjectName(u"layerCombo")
        self.layerCombo.setMinimumSize(QSize(160, 0))
        self.layerCombo.setEnabled(False)

        self.layout.addWidget(self.layerCombo)


        self.retranslateUi(SelectionLayer)

        QMetaObject.connectSlotsByName(SelectionLayer)
    # setupUi

    def retranslateUi(self, SelectionLayer):
#if QT_CONFIG(tooltip)
        self.layerCombo.setToolTip(QCoreApplication.translate("SelectionLayer", u"\u8bbe\u7f6e\u9009\u4e2d\u5bf9\u8c61\u6240\u5c5e\u56fe\u5c42", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

