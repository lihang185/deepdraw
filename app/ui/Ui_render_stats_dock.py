# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'render_stats_dock.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_RenderStatsDock(object):
    def setupUi(self, RenderStatsDock):
        if not RenderStatsDock.objectName():
            RenderStatsDock.setObjectName(u"RenderStatsDock")
        RenderStatsDock.setMinimumSize(QSize(480, 700))
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.summary = QLabel(self.dockWidgetContents)
        self.summary.setObjectName(u"summary")

        self.verticalLayout.addWidget(self.summary)

        self.tabs = QTabWidget(self.dockWidgetContents)
        self.tabs.setObjectName(u"tabs")
        self.overviewTab = QWidget()
        self.overviewTab.setObjectName(u"overviewTab")
        self.overviewLayout = QVBoxLayout(self.overviewTab)
        self.overviewLayout.setObjectName(u"overviewLayout")
        self.metrics = QTableWidget(self.overviewTab)
        if (self.metrics.columnCount() < 3):
            self.metrics.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.metrics.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.metrics.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.metrics.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.metrics.setObjectName(u"metrics")
        self.metrics.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.metrics.setSelectionMode(QAbstractItemView.NoSelection)
        self.metrics.verticalHeader().setDefaultSectionSize(24)

        self.overviewLayout.addWidget(self.metrics)

        self.tabs.addTab(self.overviewTab, "")
        self.stagesTab = QWidget()
        self.stagesTab.setObjectName(u"stagesTab")
        self.stagesLayout = QVBoxLayout(self.stagesTab)
        self.stagesLayout.setObjectName(u"stagesLayout")
        self.stages = QTableWidget(self.stagesTab)
        if (self.stages.columnCount() < 4):
            self.stages.setColumnCount(4)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.stages.setHorizontalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.stages.setHorizontalHeaderItem(1, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.stages.setHorizontalHeaderItem(2, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.stages.setHorizontalHeaderItem(3, __qtablewidgetitem6)
        self.stages.setObjectName(u"stages")
        self.stages.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stages.setSelectionMode(QAbstractItemView.NoSelection)

        self.stagesLayout.addWidget(self.stages)

        self.stagesNote = QLabel(self.stagesTab)
        self.stagesNote.setObjectName(u"stagesNote")
        self.stagesNote.setWordWrap(True)

        self.stagesLayout.addWidget(self.stagesNote)

        self.tabs.addTab(self.stagesTab, "")
        self.batchesTab = QWidget()
        self.batchesTab.setObjectName(u"batchesTab")
        self.batchesLayout = QVBoxLayout(self.batchesTab)
        self.batchesLayout.setObjectName(u"batchesLayout")
        self.batchSummary = QLabel(self.batchesTab)
        self.batchSummary.setObjectName(u"batchSummary")
        self.batchSummary.setWordWrap(True)

        self.batchesLayout.addWidget(self.batchSummary)

        self.batchReasons = QTableWidget(self.batchesTab)
        if (self.batchReasons.columnCount() < 3):
            self.batchReasons.setColumnCount(3)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.batchReasons.setHorizontalHeaderItem(0, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.batchReasons.setHorizontalHeaderItem(1, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.batchReasons.setHorizontalHeaderItem(2, __qtablewidgetitem9)
        self.batchReasons.setObjectName(u"batchReasons")
        self.batchReasons.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.batchReasons.setSelectionMode(QAbstractItemView.NoSelection)

        self.batchesLayout.addWidget(self.batchReasons)

        self.batchNote = QLabel(self.batchesTab)
        self.batchNote.setObjectName(u"batchNote")
        self.batchNote.setWordWrap(True)

        self.batchesLayout.addWidget(self.batchNote)

        self.tabs.addTab(self.batchesTab, "")

        self.verticalLayout.addWidget(self.tabs)

        self.noCull = QCheckBox(self.dockWidgetContents)
        self.noCull.setObjectName(u"noCull")

        self.verticalLayout.addWidget(self.noCull)

        self.smallObjectLayout = QHBoxLayout()
        self.smallObjectLayout.setObjectName(u"smallObjectLayout")
        self.smallObjectLabel = QLabel(self.dockWidgetContents)
        self.smallObjectLabel.setObjectName(u"smallObjectLabel")

        self.smallObjectLayout.addWidget(self.smallObjectLabel)

        self.smallObjectPercent = QDoubleSpinBox(self.dockWidgetContents)
        self.smallObjectPercent.setObjectName(u"smallObjectPercent")
        self.smallObjectPercent.setDecimals(2)
        self.smallObjectPercent.setMaximum(10.000000000000000)
        self.smallObjectPercent.setSingleStep(0.050000000000000)

        self.smallObjectLayout.addWidget(self.smallObjectPercent)


        self.verticalLayout.addLayout(self.smallObjectLayout)

        self.noEdges = QCheckBox(self.dockWidgetContents)
        self.noEdges.setObjectName(u"noEdges")

        self.verticalLayout.addWidget(self.noEdges)

        self.noShadows = QCheckBox(self.dockWidgetContents)
        self.noShadows.setObjectName(u"noShadows")

        self.verticalLayout.addWidget(self.noShadows)

        self.noTransparent = QCheckBox(self.dockWidgetContents)
        self.noTransparent.setObjectName(u"noTransparent")

        self.verticalLayout.addWidget(self.noTransparent)

        self.notes = QLabel(self.dockWidgetContents)
        self.notes.setObjectName(u"notes")
        self.notes.setWordWrap(True)

        self.verticalLayout.addWidget(self.notes)

        RenderStatsDock.setWidget(self.dockWidgetContents)

        self.retranslateUi(RenderStatsDock)

        QMetaObject.connectSlotsByName(RenderStatsDock)
    # setupUi

    def retranslateUi(self, RenderStatsDock):
        RenderStatsDock.setWindowTitle(QCoreApplication.translate("RenderStatsDock", u"\u6e32\u67d3\u7edf\u8ba1", None))
        self.summary.setText(QCoreApplication.translate("RenderStatsDock", u"\u7b49\u5f85\u89c6\u56fe\u5237\u65b0\u2026", None))
        ___qtablewidgetitem = self.metrics.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("RenderStatsDock", u"\u6307\u6807", None));
        ___qtablewidgetitem1 = self.metrics.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("RenderStatsDock", u"\u5e73\u5747 / \u5e27", None));
        ___qtablewidgetitem2 = self.metrics.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("RenderStatsDock", u"\u6700\u5927 / \u5e27", None));
        self.tabs.setTabText(self.tabs.indexOf(self.overviewTab), QCoreApplication.translate("RenderStatsDock", u"\u603b\u89c8", None))
        ___qtablewidgetitem3 = self.stages.horizontalHeaderItem(0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("RenderStatsDock", u"\u9636\u6bb5", None));
        ___qtablewidgetitem4 = self.stages.horizontalHeaderItem(1)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("RenderStatsDock", u"\u8c03\u7528/\u5e27", None));
        ___qtablewidgetitem5 = self.stages.horizontalHeaderItem(2)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("RenderStatsDock", u"\u4e09\u89d2\u5f62/\u5e27", None));
        ___qtablewidgetitem6 = self.stages.horizontalHeaderItem(3)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("RenderStatsDock", u"\u7ebf\u6bb5/\u5e27", None));
        self.stagesNote.setText(QCoreApplication.translate("RenderStatsDock", u"\u663e\u793a\u672c\u5468\u671f\u5e73\u5747\u63d0\u4ea4\u91cf\u3002\u5404\u9636\u6bb5\u5408\u8ba1\u7b49\u4e8e\u603b\u89c8\u7684 VBO \u63d0\u4ea4\u91cf\uff1b\u9634\u5f71\u5305\u542b\u9634\u5f71\u8d34\u56fe\u548c\u53e0\u52a0\u7ed8\u5236\u3002\u8017\u65f6\u8f83\u9ad8\u4f46\u63d0\u4ea4\u91cf\u5f88\u5c11\u7684\u9636\u6bb5\uff0c\u9700\u8981\u8fdb\u4e00\u6b65\u68c0\u67e5\u904d\u5386\u6216\u9a71\u52a8\u7b49\u5f85\u3002", None))
        self.tabs.setTabText(self.tabs.indexOf(self.stagesTab), QCoreApplication.translate("RenderStatsDock", u"\u5206\u9636\u6bb5\u63d0\u4ea4", None))
        self.batchSummary.setText(QCoreApplication.translate("RenderStatsDock", u"\u7b49\u5f85\u573a\u666f\u5c31\u7eea\u2026", None))
        ___qtablewidgetitem7 = self.batchReasons.horizontalHeaderItem(0)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("RenderStatsDock", u"\u672a\u5408\u6279\u9996\u8981\u539f\u56e0", None));
        ___qtablewidgetitem8 = self.batchReasons.horizontalHeaderItem(1)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("RenderStatsDock", u"\u8282\u70b9\u6570", None));
        ___qtablewidgetitem9 = self.batchReasons.horizontalHeaderItem(2)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("RenderStatsDock", u"\u5176\u4e2d\u975e\u53f6\u5b50", None));
        self.batchNote.setText(QCoreApplication.translate("RenderStatsDock", u"\u4ec5\u5728\u6b64\u9875\u663e\u793a\u65f6\u5206\u6790\uff0c\u7ed3\u679c\u6309\u573a\u666f\u53ca\u7f16\u8f91\u8def\u5f84\u7f13\u5b58\u3002\u7edf\u8ba1\u88c1\u526a\u524d\u7684\u5269\u4f59\u663e\u793a\u8282\u70b9\uff0c\u6bcf\u4e2a\u8282\u70b9\u5f52\u5165\u4e00\u4e2a\u539f\u56e0\uff0c\u4e0d\u91cd\u590d\u8ba1\u6570\u3002\u53f6\u5b50\u8282\u70b9\u672c\u8eab\u4e0d\u8db3\u4ee5\u5408\u6279\uff0c\u91cd\u70b9\u67e5\u770b\u975e\u53f6\u5b50\u8282\u70b9\u4e3a\u4f55\u88ab\u963b\u65ad\u3002\u6b64\u8bca\u65ad\u4e0d\u6539\u53d8\u5408\u6279\u89c4\u5219\u3002", None))
        self.tabs.setTabText(self.tabs.indexOf(self.batchesTab), QCoreApplication.translate("RenderStatsDock", u"\u5408\u6279\u5206\u6790", None))
        self.noCull.setText(QCoreApplication.translate("RenderStatsDock", u"\u5173\u95ed\u89c6\u9525\u88c1\u526a\uff08\u4e0e Test4 \u540c\u6b65\uff09", None))
        self.smallObjectLabel.setText(QCoreApplication.translate("RenderStatsDock", u"\u5c0f\u7269\u4f53\u8fc7\u6ee4\uff08\u5c3a\u5bf8/\u8ddd\u79bb\uff09", None))
#if QT_CONFIG(tooltip)
        self.smallObjectPercent.setToolTip(QCoreApplication.translate("RenderStatsDock", u"\u5305\u56f4\u76d2\u5bf9\u89d2\u7ebf\u957f\u5ea6/\u76f8\u673a\u5230\u5305\u56f4\u76d2\u6700\u8fd1\u8ddd\u79bb\uff0c\u5c0f\u4e8e\u9608\u503c\u65f6\u8df3\u8fc7\u6574\u4e2a\u5b50\u6811\u30020 \u5173\u95ed\uff1b\u503c\u8d8a\u5927\uff0c\u8fc7\u6ee4\u8d8a\u591a\u3002\u5173\u95ed\u7edf\u8ba1\u9762\u677f\u540e\u4ecd\u751f\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.smallObjectPercent.setSuffix(QCoreApplication.translate("RenderStatsDock", u" %", None))
        self.noEdges.setText(QCoreApplication.translate("RenderStatsDock", u"\u6d4b\u8bd5\uff1a\u9690\u85cf\u6a21\u578b\u8fb9\u7ebf\u4e0e\u8f85\u52a9\u7ebf", None))
        self.noShadows.setText(QCoreApplication.translate("RenderStatsDock", u"\u6d4b\u8bd5\uff1a\u5173\u95ed\u9634\u5f71", None))
        self.noTransparent.setText(QCoreApplication.translate("RenderStatsDock", u"\u6d4b\u8bd5\uff1a\u9690\u85cf\u900f\u660e\u9762", None))
#if QT_CONFIG(tooltip)
        self.noTransparent.setToolTip(QCoreApplication.translate("RenderStatsDock", u"\u8df3\u8fc7\u900f\u660e\u6750\u8d28\u9762\u7684\u7ed8\u5236\uff0c\u8fb9\u7ebf\u4fdd\u7559\uff1b\u4e0d\u4fee\u6539\u6a21\u578b\u6750\u8d28\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.notes.setText(QCoreApplication.translate("RenderStatsDock", u"\u6bcf 0.5 \u79d2\u6c47\u603b\u5b9e\u9645\u7ed8\u5236\u5e27\uff1b\u4e0d\u4e3b\u52a8\u5237\u65b0\u573a\u666f\u3002\u65f6\u95f4\u4e3a CPU \u63d0\u4ea4\u8017\u65f6\uff0c\u4e0d\u662f GPU \u8017\u65f6\u3002VBO \u63d0\u4ea4\u91cf\u542b\u9634\u5f71\u91cd\u590d\u7ed8\u5236\uff0c\u4e0d\u542b\u9009\u62e9\u6846\u7b49\u5373\u65f6\u8f85\u52a9\u56fe\u5f62\u3002\u5173\u95ed\u9762\u677f\u505c\u6b62\u989d\u5916\u7edf\u8ba1\uff0c\u5e76\u6062\u590d\u8fb9\u7ebf/\u9634\u5f71/\u900f\u660e\u9762\u6d4b\u8bd5\u5f00\u5173\u3002", None))
    # retranslateUi

