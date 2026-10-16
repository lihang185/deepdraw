# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'layer_dock.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_LayerDock(object):
    def setupUi(self, LayerDock):
        if not LayerDock.objectName():
            LayerDock.setObjectName(u"LayerDock")
        LayerDock.resize(351, 820)
        self.contents = QWidget()
        self.contents.setObjectName(u"contents")
        self.layout = QVBoxLayout(self.contents)
        self.layout.setObjectName(u"layout")
        self.panelSplitter = QSplitter(self.contents)
        self.panelSplitter.setObjectName(u"panelSplitter")
        self.panelSplitter.setOrientation(Qt.Vertical)
        self.panelSplitter.setChildrenCollapsible(False)
        self.layerGroup = QGroupBox(self.panelSplitter)
        self.layerGroup.setObjectName(u"layerGroup")
        self.layerLayout = QVBoxLayout(self.layerGroup)
        self.layerLayout.setObjectName(u"layerLayout")
        self.commands = QHBoxLayout()
        self.commands.setObjectName(u"commands")
        self.addButton = QToolButton(self.layerGroup)
        self.addButton.setObjectName(u"addButton")
        self.addButton.setMinimumSize(QSize(0, 25))

        self.commands.addWidget(self.addButton)

        self.deleteButton = QToolButton(self.layerGroup)
        self.deleteButton.setObjectName(u"deleteButton")
        self.deleteButton.setMinimumSize(QSize(0, 25))

        self.commands.addWidget(self.deleteButton)

        self.spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.commands.addItem(self.spacer)

        self.assignButton = QToolButton(self.layerGroup)
        self.assignButton.setObjectName(u"assignButton")
        self.assignButton.setMinimumSize(QSize(0, 25))

        self.commands.addWidget(self.assignButton)


        self.layerLayout.addLayout(self.commands)

        self.layers = QTableWidget(self.layerGroup)
        if (self.layers.columnCount() < 3):
            self.layers.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.layers.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.layers.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.layers.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.layers.setObjectName(u"layers")
        self.layers.setSelectionMode(QAbstractItemView.SingleSelection)
        self.layers.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.layerLayout.addWidget(self.layers)

        self.panelSplitter.addWidget(self.layerGroup)
        self.sceneGroup = QGroupBox(self.panelSplitter)
        self.sceneGroup.setObjectName(u"sceneGroup")
        self.sceneLayout = QVBoxLayout(self.sceneGroup)
        self.sceneLayout.setObjectName(u"sceneLayout")
        self.sceneCommands = QHBoxLayout()
        self.sceneCommands.setObjectName(u"sceneCommands")
        self.addSceneButton = QToolButton(self.sceneGroup)
        self.addSceneButton.setObjectName(u"addSceneButton")
        self.addSceneButton.setMinimumSize(QSize(0, 25))

        self.sceneCommands.addWidget(self.addSceneButton)

        self.deleteSceneButton = QToolButton(self.sceneGroup)
        self.deleteSceneButton.setObjectName(u"deleteSceneButton")
        self.deleteSceneButton.setMinimumSize(QSize(0, 25))

        self.sceneCommands.addWidget(self.deleteSceneButton)

        self.updateSceneButton = QPushButton(self.sceneGroup)
        self.updateSceneButton.setObjectName(u"updateSceneButton")
        self.updateSceneButton.setMinimumSize(QSize(0, 25))

        self.sceneCommands.addWidget(self.updateSceneButton)

        self.applySceneButton = QPushButton(self.sceneGroup)
        self.applySceneButton.setObjectName(u"applySceneButton")
        self.applySceneButton.setMinimumSize(QSize(0, 25))

        self.sceneCommands.addWidget(self.applySceneButton)


        self.sceneLayout.addLayout(self.sceneCommands)

        self.scenes = QListWidget(self.sceneGroup)
        self.scenes.setObjectName(u"scenes")
        self.scenes.setEditTriggers(QAbstractItemView.EditKeyPressed)

        self.sceneLayout.addWidget(self.scenes)

        self.panelSplitter.addWidget(self.sceneGroup)

        self.layout.addWidget(self.panelSplitter)

        LayerDock.setWidget(self.contents)

        self.retranslateUi(LayerDock)

        QMetaObject.connectSlotsByName(LayerDock)
    # setupUi

    def retranslateUi(self, LayerDock):
        LayerDock.setWindowTitle(QCoreApplication.translate("LayerDock", u"\u56fe\u5c42\u4e0e\u573a\u666f", None))
        self.layerGroup.setTitle(QCoreApplication.translate("LayerDock", u"\u56fe\u5c42\u7ba1\u7406", None))
#if QT_CONFIG(tooltip)
        self.addButton.setToolTip(QCoreApplication.translate("LayerDock", u"\u65b0\u5efa\u56fe\u5c42", None))
#endif // QT_CONFIG(tooltip)
        self.addButton.setText(QCoreApplication.translate("LayerDock", u"\uff0b", None))
#if QT_CONFIG(tooltip)
        self.deleteButton.setToolTip(QCoreApplication.translate("LayerDock", u"\u5220\u9664\u9009\u4e2d\u7684\u56fe\u5c42", None))
#endif // QT_CONFIG(tooltip)
        self.deleteButton.setText(QCoreApplication.translate("LayerDock", u"\uff0d", None))
#if QT_CONFIG(tooltip)
        self.assignButton.setToolTip(QCoreApplication.translate("LayerDock", u"\u5c06\u573a\u666f\u9009\u4e2d\u5bf9\u8c61\u5206\u914d\u5230\u5217\u8868\u9009\u4e2d\u7684\u56fe\u5c42", None))
#endif // QT_CONFIG(tooltip)
        self.assignButton.setText(QCoreApplication.translate("LayerDock", u"\u5206\u914d\u9009\u4e2d\u5bf9\u8c61", None))
        ___qtablewidgetitem = self.layers.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("LayerDock", u"\u540d\u79f0", None));
        ___qtablewidgetitem1 = self.layers.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("LayerDock", u"\u53ef\u89c1", None));
        ___qtablewidgetitem2 = self.layers.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("LayerDock", u"\u989c\u8272", None));
        self.sceneGroup.setTitle(QCoreApplication.translate("LayerDock", u"\u573a\u666f\u7ba1\u7406", None))
#if QT_CONFIG(tooltip)
        self.addSceneButton.setToolTip(QCoreApplication.translate("LayerDock", u"\u4fdd\u5b58\u5f53\u524d\u89c6\u89d2\u3001\u53ef\u89c1\u56fe\u5c42\u53ca\u592a\u9633\u5149/\u9634\u5f71\u8bbe\u7f6e\u4e3a\u65b0\u573a\u666f", None))
#endif // QT_CONFIG(tooltip)
        self.addSceneButton.setText(QCoreApplication.translate("LayerDock", u"\uff0b", None))
#if QT_CONFIG(tooltip)
        self.deleteSceneButton.setToolTip(QCoreApplication.translate("LayerDock", u"\u5220\u9664\u9009\u4e2d\u7684\u573a\u666f", None))
#endif // QT_CONFIG(tooltip)
        self.deleteSceneButton.setText(QCoreApplication.translate("LayerDock", u"\uff0d", None))
#if QT_CONFIG(tooltip)
        self.updateSceneButton.setToolTip(QCoreApplication.translate("LayerDock", u"\u5c06\u5f53\u524d\u89c6\u89d2\u3001\u53ef\u89c1\u56fe\u5c42\u53ca\u592a\u9633\u5149/\u9634\u5f71\u8bbe\u7f6e\u66f4\u65b0\u5230\u6240\u9009\u573a\u666f", None))
#endif // QT_CONFIG(tooltip)
        self.updateSceneButton.setText(QCoreApplication.translate("LayerDock", u"\u66f4\u65b0\u573a\u666f", None))
        self.applySceneButton.setText(QCoreApplication.translate("LayerDock", u"\u5207\u6362", None))
#if QT_CONFIG(tooltip)
        self.scenes.setToolTip(QCoreApplication.translate("LayerDock", u"\u53cc\u51fb\u5207\u6362\u573a\u666f\uff0c\u6309 F2 \u91cd\u547d\u540d", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

