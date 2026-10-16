# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'view_context_menu.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_ViewContextMenu(object):
    def setupUi(self, ViewContextMenu):
        if not ViewContextMenu.objectName():
            ViewContextMenu.setObjectName(u"ViewContextMenu")
        self.actionTexturePosition = QAction(ViewContextMenu)
        self.actionTexturePosition.setObjectName(u"actionTexturePosition")
        self.actionTextureRotate = QAction(ViewContextMenu)
        self.actionTextureRotate.setObjectName(u"actionTextureRotate")
        self.actionExport = QAction(ViewContextMenu)
        self.actionExport.setObjectName(u"actionExport")
        self.actionFlipFace = QAction(ViewContextMenu)
        self.actionFlipFace.setObjectName(u"actionFlipFace")
        self.actionExplode = QAction(ViewContextMenu)
        self.actionExplode.setObjectName(u"actionExplode")
        self.actionToGroup = QAction(ViewContextMenu)
        self.actionToGroup.setObjectName(u"actionToGroup")
        self.actionToComponent = QAction(ViewContextMenu)
        self.actionToComponent.setObjectName(u"actionToComponent")
        self.actionObjectProperties = QAction(ViewContextMenu)
        self.actionObjectProperties.setObjectName(u"actionObjectProperties")
        self.actionFitCamera = QAction(ViewContextMenu)
        self.actionFitCamera.setObjectName(u"actionFitCamera")

        ViewContextMenu.addAction(self.actionFitCamera)
        ViewContextMenu.addAction(self.actionObjectProperties)
        ViewContextMenu.addSeparator()
        ViewContextMenu.addAction(self.actionFlipFace)
        ViewContextMenu.addAction(self.actionTexturePosition)
        ViewContextMenu.addAction(self.actionTextureRotate)
        ViewContextMenu.addAction(self.actionExport)
        ViewContextMenu.addAction(self.actionExplode)
        ViewContextMenu.addAction(self.actionToGroup)
        ViewContextMenu.addAction(self.actionToComponent)

        self.retranslateUi(ViewContextMenu)

        QMetaObject.connectSlotsByName(ViewContextMenu)
    # setupUi

    def retranslateUi(self, ViewContextMenu):
        self.actionTexturePosition.setText(QCoreApplication.translate("ViewContextMenu", u"\u8d34\u56fe\u4f4d\u7f6e", None))
        self.actionTextureRotate.setText(QCoreApplication.translate("ViewContextMenu", u"\u8d34\u56fe\u65cb\u8f6c", None))
        self.actionExport.setText(QCoreApplication.translate("ViewContextMenu", u"\u5bfc\u51fa", None))
        self.actionFlipFace.setText(QCoreApplication.translate("ViewContextMenu", u"\u7ffb\u8f6c\u9762", None))
        self.actionExplode.setText(QCoreApplication.translate("ViewContextMenu", u"\u70b8\u5f00", None))
        self.actionToGroup.setText(QCoreApplication.translate("ViewContextMenu", u"\u8f6c\u6210Group", None))
        self.actionToComponent.setText(QCoreApplication.translate("ViewContextMenu", u"\u8f6c\u6210CComponent", None))
        self.actionObjectProperties.setText(QCoreApplication.translate("ViewContextMenu", u"\u5bf9\u8c61\u5c5e\u6027", None))
        self.actionFitCamera.setText(QCoreApplication.translate("ViewContextMenu", u"\u9002\u5e94\u89c6\u56fe", None))
        pass
    # retranslateUi

