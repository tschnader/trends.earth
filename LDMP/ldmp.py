# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LDMP - A QGIS plugin
 This plugin supports monitoring and reporting of land degradation to the UNCCD 
 and in support of the SDG Land Degradation Neutrality (LDN) target.
                              -------------------
        begin                : 2017-05-23
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Conservation International
        email                : GEF-LDMP@conservation.org
 ***************************************************************************/
"""

import os

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QApplication

from LDMP.settings import DlgSettings
from LDMP.download import DlgDownload
from LDMP.calculate import DlgCalculate
from LDMP.jobs import DlgJobs
from LDMP.timeseries import DlgTimeseries
from LDMP.reporting import DlgReporting
from LDMP.about import DlgAbout

from qgis.core import QgsMessageLog
from qgis.utils import showPluginHelp

# Initialize Qt resources from file resources.py
import LDMP.resources


def showHelp(file='index', section=None):
    locale = QSettings().value('locale/userLocale')[0:2]
    help_base_path = os.path.join(os.path.dirname(__file__), 'help', 'build', 'html')
    locale_path = os.path.join(help_base_path, locale)
    QgsMessageLog.logMessage('Checking for plugin help in {}'.format(locale_path), tag="LDMP", level=QgsMessageLog.INFO)
    if os.path.exists(locale_path):
        help_path = os.path.join(locale_path, file)
    else:
        help_path = os.path.join(help_base_path, 'en', file)
    QgsMessageLog.logMessage('Showing plugin help from {}'.format(help_path), tag="LDMP", level=QgsMessageLog.INFO)
    if section:
        showPluginHelp(filename=help_path, section=section)
    else:
        showPluginHelp(filename=help_path)


class LDMPPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale and translation
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LDMP_{}.qm'.format(locale))
        QgsMessageLog.logMessage('Using locale "{}" in path {}.'.format(locale,
                                                                        locale_path), tag="LDMP", level=QgsMessageLog.INFO)

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
                QgsMessageLog.logMessage("Translator installed.", tag="LDMP",
                                         level=QgsMessageLog.INFO)

        # Declare instance attributes
        self.actions = []
        self.menu = QApplication.translate('LDMP', u'&earth.trends')
        self.toolbar = self.iface.addToolBar(u'LDMP')
        self.toolbar.setObjectName(u'LDMP')

        self.dlg_settings = DlgSettings()
        self.dlg_download = DlgDownload()
        self.dlg_calculate = DlgCalculate()
        self.dlg_jobs = DlgJobs()
        self.dlg_timeseries = DlgTimeseries()
        self.dlg_reporting = DlgReporting()
        self.dlg_about = DlgAbout()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LDMP', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.add_action(
            ':/plugins/LDMP/icons/icon-wrench.png',
            text=QApplication.translate('LDMP', u'Settings'),
            callback=self.run_settings,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'LDMT Settings'))

        self.add_action(
            ':/plugins/LDMP/icons/icon-globe.png',
            text=QApplication.translate('LDMP', u'Download data'),
            callback=self.run_download,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'Download land degradation datasets'))

        self.add_action(
            ':/plugins/LDMP/icons/icon-calculator.png',
            text=QApplication.translate('LDMP', u'Calculate indicators'),
            callback=self.run_calculate,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'Calculate land degradation indicators'))

        self.add_action(
            ':/plugins/LDMP/icons/icon-graph.png',
            text=QApplication.translate('LDMP', u'Plot data'),
            callback=self.run_plot,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'Plot timeseries datasets'))

        self.add_action(
            ':/plugins/LDMP/icons/icon-cloud-download.png',
            text=QApplication.translate('LDMP', u'View Google Earth Engine tasks'),
            callback=self.get_jobs,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'View cloud processing tasks'))

        self.add_action(
            ':/plugins/LDMP/icons/icon-chart.png',
            text=QApplication.translate('LDMP', u'Reporting tool'),
            callback=self.run_reporting,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'Land degradation reporting'))

        self.add_action(
            ':/plugins/LDMP/icons/icon-info.png',
            text=QApplication.translate('LDMP', u'About'),
            callback=self.run_about,
            parent=self.iface.mainWindow(),
            status_tip=QApplication.translate('LDMP', 'About earth.trends'))

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                QApplication.translate('LDMP', u'&earth.trends'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run_settings(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg_settings.show()
        # Run the dialog event loop
        result = self.dlg_settings.exec_()
        # See if OK was pressed
        if result:
            pass

    def run_download(self):
        """Run method that performs all the real work"""
        # # show the dialog
        # self.dlg_download.show()
        # # Run the dialog event loop
        # result = self.dlg_download.exec_()
        # # See if OK was pressed
        # if result:
        #     pass
        QMessageBox.critical(None, QApplication.translate('LDMP', "Error"),
                             QApplication.translate('LDMP', "Raw data download coming soon!"), None)

    def run_calculate(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg_calculate.show()
        # Run the dialog event loop
        result = self.dlg_calculate.exec_()
        # See if OK was pressed
        if result:
            pass

    def get_jobs(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg_jobs.show()
        # Run the dialog event loop
        result = self.dlg_jobs.exec_()
        # See if OK was pressed
        if result:
            pass

    def run_plot(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg_timeseries.show()
        # Run the dialog event loop
        result = self.dlg_timeseries.exec_()
        # See if OK was pressed
        if result:
            pass

    def run_reporting(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg_reporting.show()
        # Run the dialog event loop
        result = self.dlg_reporting.exec_()
        # See if OK was pressed
        if result:
            pass

    def run_about(self):
        """Run method that performs all the real work"""
        #showHelp()
        self.dlg_about.show()
        # Run the dialog event loop
        result = self.dlg_about.exec_()
        # See if OK was pressed
        if result:
            pass
