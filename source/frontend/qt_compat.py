#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

from qt_config import qt as qt_config


# ------------------------------------------------------------------------------------------------------------
# Qt 5
# ------------------------------------------------------------------------------------------------------------

if qt_config == 5:
    # QtCore
    from PyQt5.QtCore import (
        Qt,
        QBuffer,
        QEvent,
        QEventLoop,
        QFileInfo,
        QIODevice,
        QLineF,
        QMimeData,
        QModelIndex,
        QObject,
        QPoint,
        QPointF,
        QRect,
        QRectF,
        QSize,
        QTimer,
        QThread,
        QSettings,
        qCritical,
        qFatal,
        qWarning,
        pyqtSignal,
        pyqtSlot,
        QAbstractAnimation,
        QEasingCurve,
        QVariantAnimation,
    )

    # QtGui
    from PyQt5.QtGui import (
        QAction,
        QBrush,
        QColor,
        QConicalGradient,
        QCursor,
        QFont,
        QFontDatabase,
        QFontMetrics,
        QImage,
        QImageWriter,
        QKeySequence,
        QLinearGradient,
        QMouseEvent,
        QPainter,
        QPainterPath,
        QRadialGradient,
        QPainterPathStroker,
        QPalette,
        QPen,
        QPixmap,
        QPolygonF,
        QSurfaceFormat,
        QTextCursor,
        QIcon,
        QDesktopServices,
    )
    from PyQt5.QtCore import QUrl

    # QtWidgets
    from PyQt5.QtWidgets import (
        QAbstractItemView,
        QAbstractSpinBox,
        QActionGroup,
        QApplication,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDial,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
        QFileSystemModel,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGraphicsColorizeEffect,
        QGraphicsDropShadowEffect,
        QGraphicsItem,
        QGraphicsLineItem,
        QGraphicsObject,
        QGraphicsPathItem,
        QGraphicsProxyWidget,
        QGraphicsRectItem,
        QGraphicsSimpleTextItem,
        QGraphicsTextItem,
        QGraphicsScene,
        QGraphicsView,
        QGroupBox,
        QHeaderView,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLayout,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QShortcut,
        QSlider,
        QSpacerItem,
        QSpinBox,
        QSplitter,
        QStackedWidget,
        QSizePolicy,
        QStyle,
        QStyleOptionButton,
        QSystemTrayIcon,
        QTabWidget,
        QTableWidget,
        QTextEdit,
        QTableWidgetItem,
        QToolButton,
        QVBoxLayout,
        QWidget,
        QWidgetAction,
    )

    try:
        from PyQt5.QtSvg import QGraphicsSvgItem, QSvgRenderer, QSvgWidget
    except ImportError:
        QGraphicsSvgItem = None
        QSvgRenderer = None
        QSvgWidget = None

    # QtOpenGL
    try:
        from PyQt5.QtOpenGL import QGLWidget
    except ImportError:
        QGLWidget = None


# ------------------------------------------------------------------------------------------------------------
# Qt 6
# ------------------------------------------------------------------------------------------------------------

elif qt_config == 6:
    # QtCore
    from PyQt6.QtCore import (
        QBuffer,
        QEvent,
        QEventLoop,
        QFileInfo,
        QIODevice,
        QLineF,
        QMimeData,
        QModelIndex,
        QObject,
        QPoint,
        QPointF,
        QRect,
        QRectF,
        QSize,
        Qt,
        QTimer,
        QSettings,
        QThread,
        qCritical,
        qFatal,
        qWarning,
        pyqtSignal,
        pyqtSlot,
        QAbstractAnimation,
        QEasingCurve,
        QVariantAnimation,
    )

    # QtGui
    from PyQt6.QtGui import (
        QAction,
        QActionGroup,
        QBrush,
        QColor,
        QConicalGradient,
        QCursor,
        QFileSystemModel,
        QFont,
        QFontDatabase,
        QFontMetrics,
        QImage,
        QImageWriter,
        QKeySequence,
        QLinearGradient,
        QMouseEvent,
        QPainter,
        QPainterPath,
        QRadialGradient,
        QPainterPathStroker,
        QPalette,
        QPen,
        QPixmap,
        QPolygonF,
        QShortcut,
        QSurfaceFormat,
        QTextCursor,
        QIcon,
        QDesktopServices,
    )
    from PyQt6.QtCore import QUrl

    # QtWidgets
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QAbstractSpinBox,
        QApplication,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDial,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGraphicsColorizeEffect,
        QGraphicsDropShadowEffect,
        QGraphicsItem,
        QGraphicsLineItem,
        QGraphicsObject,
        QGraphicsPathItem,
        QGraphicsProxyWidget,
        QGraphicsRectItem,
        QGraphicsSimpleTextItem,
        QGraphicsTextItem,
        QGraphicsScene,
        QGraphicsView,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QLayout,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSpacerItem,
        QSpinBox,
        QSplitter,
        QStackedWidget,
        QStyle,
        QStyleOptionButton,
        QSystemTrayIcon,
        QTextEdit,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QToolButton,
        QVBoxLayout,
        QWidget,
        QWidgetAction,
    )

    try:
        from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError:
        QGraphicsSvgItem = None
        QSvgRenderer = None
        QSvgWidget = None

    # Qt6 moved QOpenGLWidget into QtOpenGLWidgets.
    #
    # Carla's code historically calls this QGLWidget, so expose the
    # Qt6 equivalent under the old name.
    try:
        from PyQt6.QtOpenGLWidgets import QOpenGLWidget

        QGLWidget = QOpenGLWidget
    except ImportError:
        QGLWidget = None

    # --------------------------------------------------------------------------------------------------------
    # Qt compatibility aliases
    # --------------------------------------------------------------------------------------------------------

    # --------------------------------------------------------------------------------------------------------
    # Qt.AlignmentFlag
    # --------------------------------------------------------------------------------------------------------

    Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
    Qt.AlignLeft = Qt.AlignmentFlag.AlignLeft
    Qt.AlignRight = Qt.AlignmentFlag.AlignRight
    Qt.AlignHCenter = Qt.AlignmentFlag.AlignHCenter
    Qt.AlignVCenter = Qt.AlignmentFlag.AlignVCenter
    Qt.AlignTop = Qt.AlignmentFlag.AlignTop
    Qt.AlignBottom = Qt.AlignmentFlag.AlignBottom

    # --------------------------------------------------------------------------------------------------------
    # Qt.ApplicationAttribute
    # --------------------------------------------------------------------------------------------------------

    Qt.AA_DontShowIconsInMenus = Qt.ApplicationAttribute.AA_DontShowIconsInMenus

    # --------------------------------------------------------------------------------------------------------
    # Qt.ArrowType
    # --------------------------------------------------------------------------------------------------------

    Qt.DownArrow = Qt.ArrowType.DownArrow
    Qt.LeftArrow = Qt.ArrowType.LeftArrow
    Qt.RightArrow = Qt.ArrowType.RightArrow
    Qt.UpArrow = Qt.ArrowType.UpArrow

    # --------------------------------------------------------------------------------------------------------
    # Qt.AspectRatioMode
    # --------------------------------------------------------------------------------------------------------

    Qt.IgnoreAspectRatio = Qt.AspectRatioMode.IgnoreAspectRatio

    Qt.KeepAspectRatio = Qt.AspectRatioMode.KeepAspectRatio

    # --------------------------------------------------------------------------------------------------------
    # Qt.BrushStyle
    # --------------------------------------------------------------------------------------------------------

    Qt.NoBrush = Qt.BrushStyle.NoBrush

    # --------------------------------------------------------------------------------------------------------
    # Qt.ContextMenuPolicy
    # --------------------------------------------------------------------------------------------------------

    Qt.CustomContextMenu = Qt.ContextMenuPolicy.CustomContextMenu

    Qt.NoContextMenu = Qt.ContextMenuPolicy.NoContextMenu

    # --------------------------------------------------------------------------------------------------------
    # Qt.CursorShape
    # --------------------------------------------------------------------------------------------------------

    Qt.ArrowCursor = Qt.CursorShape.ArrowCursor
    Qt.BusyCursor = Qt.CursorShape.BusyCursor
    Qt.ClosedHandCursor = Qt.CursorShape.ClosedHandCursor
    Qt.CrossCursor = Qt.CursorShape.CrossCursor
    Qt.ForbiddenCursor = Qt.CursorShape.ForbiddenCursor
    Qt.IBeamCursor = Qt.CursorShape.IBeamCursor
    Qt.OpenHandCursor = Qt.CursorShape.OpenHandCursor
    Qt.PointingHandCursor = Qt.CursorShape.PointingHandCursor
    Qt.SizeAllCursor = Qt.CursorShape.SizeAllCursor
    Qt.SizeHorCursor = Qt.CursorShape.SizeHorCursor
    Qt.SizeVerCursor = Qt.CursorShape.SizeVerCursor
    Qt.WaitCursor = Qt.CursorShape.WaitCursor

    # --------------------------------------------------------------------------------------------------------
    # Qt.GlobalColor
    # --------------------------------------------------------------------------------------------------------

    Qt.black = Qt.GlobalColor.black
    Qt.blue = Qt.GlobalColor.blue
    Qt.cyan = Qt.GlobalColor.cyan
    Qt.darkGray = Qt.GlobalColor.darkGray
    Qt.gray = Qt.GlobalColor.gray
    Qt.green = Qt.GlobalColor.green
    Qt.red = Qt.GlobalColor.red
    Qt.transparent = Qt.GlobalColor.transparent
    Qt.white = Qt.GlobalColor.white
    Qt.yellow = Qt.GlobalColor.yellow

    # --------------------------------------------------------------------------------------------------------
    # Qt.ItemDataRole
    # --------------------------------------------------------------------------------------------------------

    Qt.UserRole = Qt.ItemDataRole.UserRole

    # --------------------------------------------------------------------------------------------------------
    # Qt.ItemFlag
    # --------------------------------------------------------------------------------------------------------

    Qt.ItemIsDragEnabled = Qt.ItemFlag.ItemIsDragEnabled
    Qt.ItemIsDropEnabled = Qt.ItemFlag.ItemIsDropEnabled
    Qt.ItemIsEnabled = Qt.ItemFlag.ItemIsEnabled
    Qt.ItemIsSelectable = Qt.ItemFlag.ItemIsSelectable
    Qt.ItemIsEditable = Qt.ItemFlag.ItemIsEditable
    Qt.ItemIsUserCheckable = Qt.ItemFlag.ItemIsUserCheckable

    # --------------------------------------------------------------------------------------------------------
    # Qt.ItemSelectionMode
    # --------------------------------------------------------------------------------------------------------

    Qt.ContainsItemShape = Qt.ItemSelectionMode.ContainsItemShape

    Qt.IntersectsItemShape = Qt.ItemSelectionMode.IntersectsItemShape

    Qt.ContainsItemBoundingRect = Qt.ItemSelectionMode.ContainsItemBoundingRect

    Qt.IntersectsItemBoundingRect = Qt.ItemSelectionMode.IntersectsItemBoundingRect

    # --------------------------------------------------------------------------------------------------------
    # Qt.Key
    # --------------------------------------------------------------------------------------------------------

    for _key_name in (
        "Key_0",
        "Key_1",
        "Key_2",
        "Key_3",
        "Key_4",
        "Key_5",
        "Key_6",
        "Key_7",
        "Key_8",
        "Key_9",
        "Key_A",
        "Key_B",
        "Key_C",
        "Key_D",
        "Key_E",
        "Key_F",
        "Key_G",
        "Key_H",
        "Key_I",
        "Key_J",
        "Key_K",
        "Key_L",
        "Key_M",
        "Key_N",
        "Key_O",
        "Key_P",
        "Key_Q",
        "Key_R",
        "Key_S",
        "Key_T",
        "Key_U",
        "Key_V",
        "Key_W",
        "Key_X",
        "Key_Y",
        "Key_Z",
        "Key_Agrave",
        "Key_Backspace",
        "Key_Ccedilla",
        "Key_Comma",
        "Key_Delete",
        "Key_Down",
        "Key_End",
        "Key_Enter",
        "Key_Escape",
        "Key_Eacute",
        "Key_Egrave",
        "Key_Home",
        "Key_Left",
        "Key_Minus",
        "Key_PageDown",
        "Key_PageUp",
        "Key_ParenLeft",
        "Key_Plus",
        "Key_QuoteDbl",
        "Key_Return",
        "Key_Right",
        "Key_Space",
        "Key_Up",
    ):
        setattr(Qt, _key_name, getattr(Qt.Key, _key_name))

    # --------------------------------------------------------------------------------------------------------
    # Qt.KeyboardModifier
    # --------------------------------------------------------------------------------------------------------

    Qt.AltModifier = Qt.KeyboardModifier.AltModifier
    Qt.ControlModifier = Qt.KeyboardModifier.ControlModifier
    Qt.MetaModifier = Qt.KeyboardModifier.MetaModifier
    Qt.NoModifier = Qt.KeyboardModifier.NoModifier
    Qt.ShiftModifier = Qt.KeyboardModifier.ShiftModifier

    # --------------------------------------------------------------------------------------------------------
    # Qt.MouseButton
    # --------------------------------------------------------------------------------------------------------

    Qt.LeftButton = Qt.MouseButton.LeftButton
    Qt.MiddleButton = Qt.MouseButton.MiddleButton
    Qt.RightButton = Qt.MouseButton.RightButton

    # --------------------------------------------------------------------------------------------------------
    # Qt.TextElideMode
    # --------------------------------------------------------------------------------------------------------

    Qt.ElideLeft = Qt.TextElideMode.ElideLeft
    Qt.ElideRight = Qt.TextElideMode.ElideRight
    Qt.ElideMiddle = Qt.TextElideMode.ElideMiddle
    Qt.ElideNone = Qt.TextElideMode.ElideNone

    # --------------------------------------------------------------------------------------------------------
    # Qt.MouseEventSource
    # --------------------------------------------------------------------------------------------------------

    Qt.MouseEventSynthesizedByApplication = (
        Qt.MouseEventSource.MouseEventSynthesizedByApplication
    )

    # --------------------------------------------------------------------------------------------------------
    # Qt.Orientation
    # --------------------------------------------------------------------------------------------------------

    Qt.Horizontal = Qt.Orientation.Horizontal
    Qt.Vertical = Qt.Orientation.Vertical

    # --------------------------------------------------------------------------------------------------------
    # Qt.PenCapStyle
    # --------------------------------------------------------------------------------------------------------

    Qt.FlatCap = Qt.PenCapStyle.FlatCap
    Qt.RoundCap = Qt.PenCapStyle.RoundCap
    Qt.SquareCap = Qt.PenCapStyle.SquareCap

    # --------------------------------------------------------------------------------------------------------
    # Qt.PenJoinStyle
    # --------------------------------------------------------------------------------------------------------

    Qt.MiterJoin = Qt.PenJoinStyle.MiterJoin
    Qt.RoundJoin = Qt.PenJoinStyle.RoundJoin
    Qt.BevelJoin = Qt.PenJoinStyle.BevelJoin

    # --------------------------------------------------------------------------------------------------------
    # Qt.PenStyle
    # --------------------------------------------------------------------------------------------------------

    Qt.DashLine = Qt.PenStyle.DashLine
    Qt.DotLine = Qt.PenStyle.DotLine
    Qt.NoPen = Qt.PenStyle.NoPen
    Qt.SolidLine = Qt.PenStyle.SolidLine

    # --------------------------------------------------------------------------------------------------------
    # Qt.ScrollBarPolicy
    # --------------------------------------------------------------------------------------------------------

    Qt.ScrollBarAlwaysOn = Qt.ScrollBarPolicy.ScrollBarAlwaysOn

    Qt.ScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    Qt.ScrollBarAsNeeded = Qt.ScrollBarPolicy.ScrollBarAsNeeded

    # --------------------------------------------------------------------------------------------------------
    # Qt.ShortcutContext
    # --------------------------------------------------------------------------------------------------------

    Qt.WidgetShortcut = Qt.ShortcutContext.WidgetShortcut
    Qt.WidgetWithChildrenShortcut = Qt.ShortcutContext.WidgetWithChildrenShortcut
    Qt.WindowShortcut = Qt.ShortcutContext.WindowShortcut
    Qt.ApplicationShortcut = Qt.ShortcutContext.ApplicationShortcut

    # --------------------------------------------------------------------------------------------------------
    # Qt.SortOrder
    # --------------------------------------------------------------------------------------------------------

    Qt.AscendingOrder = Qt.SortOrder.AscendingOrder
    Qt.DescendingOrder = Qt.SortOrder.DescendingOrder

    # --------------------------------------------------------------------------------------------------------
    # Qt.TextFormat
    # --------------------------------------------------------------------------------------------------------

    Qt.RichText = Qt.TextFormat.RichText
    Qt.PlainText = Qt.TextFormat.PlainText
    Qt.AutoText = Qt.TextFormat.AutoText

    # --------------------------------------------------------------------------------------------------------
    # Qt.TextInteractionFlag
    # --------------------------------------------------------------------------------------------------------

    Qt.TextSelectableByMouse = Qt.TextInteractionFlag.TextSelectableByMouse

    Qt.TextSelectableByKeyboard = Qt.TextInteractionFlag.TextSelectableByKeyboard

    # --------------------------------------------------------------------------------------------------------
    # Qt.ToolButtonStyle
    # --------------------------------------------------------------------------------------------------------

    Qt.ToolButtonIconOnly = Qt.ToolButtonStyle.ToolButtonIconOnly

    Qt.ToolButtonTextBesideIcon = Qt.ToolButtonStyle.ToolButtonTextBesideIcon

    Qt.ToolButtonTextOnly = Qt.ToolButtonStyle.ToolButtonTextOnly

    # --------------------------------------------------------------------------------------------------------
    # Qt.TransformationMode
    # --------------------------------------------------------------------------------------------------------

    Qt.SmoothTransformation = Qt.TransformationMode.SmoothTransformation

    Qt.FastTransformation = Qt.TransformationMode.FastTransformation

    # --------------------------------------------------------------------------------------------------------
    # Qt.WidgetAttribute
    # --------------------------------------------------------------------------------------------------------

    Qt.WA_LayoutUsesWidgetRect = Qt.WidgetAttribute.WA_LayoutUsesWidgetRect

    Qt.WA_OpaquePaintEvent = Qt.WidgetAttribute.WA_OpaquePaintEvent

    # --------------------------------------------------------------------------------------------------------
    # Qt.WindowModality
    # --------------------------------------------------------------------------------------------------------

    Qt.WindowModal = Qt.WindowModality.WindowModal

    # --------------------------------------------------------------------------------------------------------
    # Qt.WindowState
    # --------------------------------------------------------------------------------------------------------

    Qt.WindowActive = Qt.WindowState.WindowActive
    Qt.WindowMinimized = Qt.WindowState.WindowMinimized
    Qt.WindowMaximized = Qt.WindowState.WindowMaximized
    Qt.WindowFullScreen = Qt.WindowState.WindowFullScreen

    # --------------------------------------------------------------------------------------------------------
    # Qt.WindowType
    # --------------------------------------------------------------------------------------------------------

    Qt.MSWindowsFixedSizeDialogHint = Qt.WindowType.MSWindowsFixedSizeDialogHint

    Qt.WindowContextHelpButtonHint = Qt.WindowType.WindowContextHelpButtonHint

    # --------------------------------------------------------------------------------------------------------
    # QAbstractItemView
    # --------------------------------------------------------------------------------------------------------

    QAbstractItemView.DropOnly = QAbstractItemView.DragDropMode.DropOnly

    QAbstractItemView.SingleSelection = QAbstractItemView.SelectionMode.SingleSelection

    QAbstractItemView.MultiSelection = QAbstractItemView.SelectionMode.MultiSelection

    QAbstractItemView.ExtendedSelection = (
        QAbstractItemView.SelectionMode.ExtendedSelection
    )

    QAbstractItemView.NoSelection = QAbstractItemView.SelectionMode.NoSelection

    # --------------------------------------------------------------------------------------------------------
    # QAbstractSpinBox
    # --------------------------------------------------------------------------------------------------------

    QAbstractSpinBox.NoButtons = QAbstractSpinBox.ButtonSymbols.NoButtons

    QAbstractSpinBox.UpDownArrows = QAbstractSpinBox.ButtonSymbols.UpDownArrows

    QAbstractSpinBox.PlusMinus = QAbstractSpinBox.ButtonSymbols.PlusMinus

    QAbstractSpinBox.StepNone = QAbstractSpinBox.StepEnabledFlag.StepNone

    QAbstractSpinBox.StepDownEnabled = QAbstractSpinBox.StepEnabledFlag.StepDownEnabled

    QAbstractSpinBox.StepUpEnabled = QAbstractSpinBox.StepEnabledFlag.StepUpEnabled

    QAbstractSpinBox.StepUpEnabled = QAbstractSpinBox.StepEnabledFlag.StepUpEnabled

    # --------------------------------------------------------------------------------------------------------
    # QApplication
    # --------------------------------------------------------------------------------------------------------

    QApplication.exec_ = lambda a: a.exec()

    # --------------------------------------------------------------------------------------------------------
    # QColorDialog
    # --------------------------------------------------------------------------------------------------------

    QColorDialog.DontUseNativeDialog = (
        QColorDialog.ColorDialogOption.DontUseNativeDialog
    )

    # --------------------------------------------------------------------------------------------------------
    # QDialog
    # --------------------------------------------------------------------------------------------------------

    QDialog.exec_ = lambda d: d.exec()

    # --------------------------------------------------------------------------------------------------------
    # QDialogButtonBox
    # --------------------------------------------------------------------------------------------------------

    for _button_name in (
        "Ok",
        "Cancel",
        "Close",
        "Save",
        "Discard",
        "Reset",
        "Apply",
        "Yes",
        "No",
    ):
        setattr(
            QDialogButtonBox,
            _button_name,
            getattr(QDialogButtonBox.StandardButton, _button_name),
        )

    # --------------------------------------------------------------------------------------------------------
    # QEvent
    # --------------------------------------------------------------------------------------------------------

    QEvent.EnabledChange = QEvent.Type.EnabledChange
    QEvent.MouseButtonPress = QEvent.Type.MouseButtonPress
    QEvent.MouseButtonRelease = QEvent.Type.MouseButtonRelease
    QEvent.MouseMove = QEvent.Type.MouseMove
    QEvent.MouseButtonDblClick = QEvent.Type.MouseButtonDblClick
    QEvent.PaletteChange = QEvent.Type.PaletteChange
    QEvent.StyleChange = QEvent.Type.StyleChange
    QEvent.User = QEvent.Type.User
    QEvent.WindowStateChange = QEvent.Type.WindowStateChange
    QEvent.Resize = QEvent.Type.Resize
    QEvent.Move = QEvent.Type.Move
    QEvent.Show = QEvent.Type.Show
    QEvent.Hide = QEvent.Type.Hide
    QEvent.Close = QEvent.Type.Close
    QEvent.KeyPress = QEvent.Type.KeyPress
    QEvent.KeyRelease = QEvent.Type.KeyRelease

    # --------------------------------------------------------------------------------------------------------
    # QEventLoop
    # --------------------------------------------------------------------------------------------------------

    QEventLoop.ExcludeUserInputEvents = (
        QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
    )

    QEventLoop.AllEvents = QEventLoop.ProcessEventsFlag.AllEvents

    # --------------------------------------------------------------------------------------------------------
    # QFileDialog
    # --------------------------------------------------------------------------------------------------------

    QFileDialog.AcceptSave = QFileDialog.AcceptMode.AcceptSave

    QFileDialog.AcceptOpen = QFileDialog.AcceptMode.AcceptOpen

    QFileDialog.AnyFile = QFileDialog.FileMode.AnyFile

    QFileDialog.ExistingFile = QFileDialog.FileMode.ExistingFile

    QFileDialog.ExistingFiles = QFileDialog.FileMode.ExistingFiles

    QFileDialog.Directory = QFileDialog.FileMode.Directory

    QFileDialog.DontUseCustomDirectoryIcons = (
        QFileDialog.Option.DontUseCustomDirectoryIcons
    )

    QFileDialog.ShowDirsOnly = QFileDialog.Option.ShowDirsOnly

    # --------------------------------------------------------------------------------------------------------
    # QFont
    # --------------------------------------------------------------------------------------------------------

    QFont.AllUppercase = QFont.Capitalization.AllUppercase

    QFont.SmallCaps = QFont.Capitalization.SmallCaps

    QFont.MixedCase = QFont.Capitalization.MixedCase

    QFont.Bold = QFont.Weight.Bold
    QFont.Normal = QFont.Weight.Normal

    # --------------------------------------------------------------------------------------------------------
    # QFrame
    # --------------------------------------------------------------------------------------------------------

    QFrame.NoFrame = QFrame.Shape.NoFrame
    QFrame.Box = QFrame.Shape.Box
    QFrame.Panel = QFrame.Shape.Panel
    QFrame.StyledPanel = QFrame.Shape.StyledPanel
    QFrame.HLine = QFrame.Shape.HLine
    QFrame.VLine = QFrame.Shape.VLine

    QFrame.Plain = QFrame.Shadow.Plain
    QFrame.Raised = QFrame.Shadow.Raised
    QFrame.Sunken = QFrame.Shadow.Sunken

    # --------------------------------------------------------------------------------------------------------
    # QGraphicsItem
    # --------------------------------------------------------------------------------------------------------

    QGraphicsItem.ItemSelectedHasChanged = (
        QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged
    )

    QGraphicsItem.ItemPositionChange = (
        QGraphicsItem.GraphicsItemChange.ItemPositionChange
    )

    QGraphicsItem.ItemPositionHasChanged = (
        QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
    )

    QGraphicsItem.ItemIsFocusable = QGraphicsItem.GraphicsItemFlag.ItemIsFocusable

    QGraphicsItem.ItemIsMovable = QGraphicsItem.GraphicsItemFlag.ItemIsMovable

    QGraphicsItem.ItemIsSelectable = QGraphicsItem.GraphicsItemFlag.ItemIsSelectable

    QGraphicsItem.ItemSendsGeometryChanges = (
        QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
    )

    # --------------------------------------------------------------------------------------------------------
    # QGraphicsScene
    # --------------------------------------------------------------------------------------------------------

    QGraphicsScene.NoIndex = QGraphicsScene.ItemIndexMethod.NoIndex

    # --------------------------------------------------------------------------------------------------------
    # QGraphicsView
    # --------------------------------------------------------------------------------------------------------

    QGraphicsView.NoDrag = QGraphicsView.DragMode.NoDrag

    QGraphicsView.ScrollHandDrag = QGraphicsView.DragMode.ScrollHandDrag

    QGraphicsView.RubberBandDrag = QGraphicsView.DragMode.RubberBandDrag

    QGraphicsView.FullViewportUpdate = (
        QGraphicsView.ViewportUpdateMode.FullViewportUpdate
    )

    QGraphicsView.MinimalViewportUpdate = (
        QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate
    )

    QGraphicsView.SmartViewportUpdate = (
        QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
    )

    # --------------------------------------------------------------------------------------------------------
    # QImage
    # --------------------------------------------------------------------------------------------------------

    QImage.Format_ARGB32 = QImage.Format.Format_ARGB32
    QImage.Format_RGB32 = QImage.Format.Format_RGB32

    # --------------------------------------------------------------------------------------------------------
    # QHeaderView
    # --------------------------------------------------------------------------------------------------------

    QHeaderView.Fixed = QHeaderView.ResizeMode.Fixed
    QHeaderView.Stretch = QHeaderView.ResizeMode.Stretch
    QHeaderView.ResizeToContents = QHeaderView.ResizeMode.ResizeToContents

    # --------------------------------------------------------------------------------------------------------
    # QLineEdit
    # --------------------------------------------------------------------------------------------------------

    QLineEdit.Normal = QLineEdit.EchoMode.Normal
    QLineEdit.NoEcho = QLineEdit.EchoMode.NoEcho
    QLineEdit.Password = QLineEdit.EchoMode.Password
    QLineEdit.PasswordEchoOnEdit = QLineEdit.EchoMode.PasswordEchoOnEdit

    # --------------------------------------------------------------------------------------------------------
    # QListWidgetItem
    # --------------------------------------------------------------------------------------------------------

    QListWidgetItem.UserType = QListWidgetItem.ItemType.UserType

    # --------------------------------------------------------------------------------------------------------
    # QMenu
    # --------------------------------------------------------------------------------------------------------

    QMenu.exec_ = lambda m, *args: m.exec(*args)

    # --------------------------------------------------------------------------------------------------------
    # QMessageBox
    # --------------------------------------------------------------------------------------------------------

    QMessageBox.exec_ = lambda mb: mb.exec()

    for _button_name in (
        "Ok",
        "Open",
        "Save",
        "Cancel",
        "Close",
        "Yes",
        "No",
        "Abort",
        "Retry",
        "Ignore",
        "Discard",
        "Apply",
        "Reset",
    ):
        if hasattr(QMessageBox.StandardButton, _button_name):
            setattr(
                QMessageBox,
                _button_name,
                getattr(QMessageBox.StandardButton, _button_name),
            )

    QMessageBox.Critical = QMessageBox.Icon.Critical
    QMessageBox.Information = QMessageBox.Icon.Information
    QMessageBox.Question = QMessageBox.Icon.Question
    QMessageBox.Warning = QMessageBox.Icon.Warning
    QMessageBox.NoIcon = QMessageBox.Icon.NoIcon

    # --------------------------------------------------------------------------------------------------------
    # QPainter
    # --------------------------------------------------------------------------------------------------------

    QPainter.CompositionMode_Difference = (
        QPainter.CompositionMode.CompositionMode_Difference
    )

    QPainter.CompositionMode_Multiply = (
        QPainter.CompositionMode.CompositionMode_Multiply
    )

    QPainter.CompositionMode_Plus = QPainter.CompositionMode.CompositionMode_Plus

    QPainter.CompositionMode_SourceOver = (
        QPainter.CompositionMode.CompositionMode_SourceOver
    )

    QPainter.Antialiasing = QPainter.RenderHint.Antialiasing

    QPainter.SmoothPixmapTransform = QPainter.RenderHint.SmoothPixmapTransform

    QPainter.TextAntialiasing = QPainter.RenderHint.TextAntialiasing

    # --------------------------------------------------------------------------------------------------------
    # QPalette
    # --------------------------------------------------------------------------------------------------------

    QPalette.Active = QPalette.ColorGroup.Active
    QPalette.Disabled = QPalette.ColorGroup.Disabled
    QPalette.Inactive = QPalette.ColorGroup.Inactive

    QPalette.AlternateBase = QPalette.ColorRole.AlternateBase
    QPalette.Base = QPalette.ColorRole.Base
    QPalette.BrightText = QPalette.ColorRole.BrightText
    QPalette.Button = QPalette.ColorRole.Button
    QPalette.ButtonText = QPalette.ColorRole.ButtonText
    QPalette.Dark = QPalette.ColorRole.Dark
    QPalette.Highlight = QPalette.ColorRole.Highlight
    QPalette.HighlightedText = QPalette.ColorRole.HighlightedText
    QPalette.Light = QPalette.ColorRole.Light
    QPalette.Link = QPalette.ColorRole.Link
    QPalette.LinkVisited = QPalette.ColorRole.LinkVisited
    QPalette.Mid = QPalette.ColorRole.Mid
    QPalette.Midlight = QPalette.ColorRole.Midlight
    QPalette.Shadow = QPalette.ColorRole.Shadow
    QPalette.Text = QPalette.ColorRole.Text
    QPalette.ToolTipBase = QPalette.ColorRole.ToolTipBase
    QPalette.ToolTipText = QPalette.ColorRole.ToolTipText
    QPalette.Window = QPalette.ColorRole.Window
    QPalette.WindowText = QPalette.ColorRole.WindowText

    QPalette.Background = QPalette.Window

    # --------------------------------------------------------------------------------------------------------
    # QSizePolicy
    # --------------------------------------------------------------------------------------------------------

    QSizePolicy.Fixed = QSizePolicy.Policy.Fixed
    QSizePolicy.Minimum = QSizePolicy.Policy.Minimum
    QSizePolicy.Maximum = QSizePolicy.Policy.Maximum
    QSizePolicy.Preferred = QSizePolicy.Policy.Preferred
    QSizePolicy.Expanding = QSizePolicy.Policy.Expanding
    QSizePolicy.MinimumExpanding = QSizePolicy.Policy.MinimumExpanding
    QSizePolicy.Ignored = QSizePolicy.Policy.Ignored

    # --------------------------------------------------------------------------------------------------------
    # QStyle
    # --------------------------------------------------------------------------------------------------------

    QStyle.State_Selected = QStyle.StateFlag.State_Selected

    QStyle.State_Enabled = QStyle.StateFlag.State_Enabled

    QStyle.State_MouseOver = QStyle.StateFlag.State_MouseOver

    QStyle.State_Active = QStyle.StateFlag.State_Active

    # --------------------------------------------------------------------------------------------------------
    # QEvent
    # --------------------------------------------------------------------------------------------------------

    QEvent.FocusIn = QEvent.Type.FocusIn
    QEvent.FocusOut = QEvent.Type.FocusOut
    # --------------------------------------------------------------------------------------------------------
    # Qt.MouseButton
    # --------------------------------------------------------------------------------------------------------

    Qt.NoButton = Qt.MouseButton.NoButton
    Qt.LeftButton = Qt.MouseButton.LeftButton
    Qt.MiddleButton = Qt.MouseButton.MiddleButton
    Qt.RightButton = Qt.MouseButton.RightButton

    # --------------------------------------------------------------------------------------------------------
    # Qt.CursorShape
    # --------------------------------------------------------------------------------------------------------

    Qt.ArrowCursor = Qt.CursorShape.ArrowCursor
    Qt.PointingHandCursor = Qt.CursorShape.PointingHandCursor
    Qt.SizeAllCursor = Qt.CursorShape.SizeAllCursor
    Qt.SizeHorCursor = Qt.CursorShape.SizeHorCursor
    Qt.SizeVerCursor = Qt.CursorShape.SizeVerCursor
    Qt.SizeFDiagCursor = Qt.CursorShape.SizeFDiagCursor
    Qt.SizeBDiagCursor = Qt.CursorShape.SizeBDiagCursor
    Qt.ClosedHandCursor = Qt.CursorShape.ClosedHandCursor
    Qt.OpenHandCursor = Qt.CursorShape.OpenHandCursor

    # --------------------------------------------------------------------------------------------------------
    # Qt.TextInteractionFlag
    # --------------------------------------------------------------------------------------------------------

    Qt.NoTextInteraction = Qt.TextInteractionFlag.NoTextInteraction
    Qt.TextSelectableByMouse = Qt.TextInteractionFlag.TextSelectableByMouse
    Qt.TextSelectableByKeyboard = Qt.TextInteractionFlag.TextSelectableByKeyboard
    Qt.TextEditable = Qt.TextInteractionFlag.TextEditable
    Qt.TextEditorInteraction = Qt.TextInteractionFlag.TextEditorInteraction
    Qt.TextBrowserInteraction = Qt.TextInteractionFlag.TextBrowserInteraction

    # --------------------------------------------------------------------------------------------------------
    # Qt.WindowModality
    # --------------------------------------------------------------------------------------------------------

    Qt.NonModal = Qt.WindowModality.NonModal
    Qt.WindowModal = Qt.WindowModality.WindowModal
    Qt.ApplicationModal = Qt.WindowModality.ApplicationModal

# ------------------------------------------------------------------------------------------------------------
# Version information
# ------------------------------------------------------------------------------------------------------------

if qt_config == 5:
    try:
        from PyQt5.Qt import PYQT_VERSION
    except ImportError:
        PYQT_VERSION = 0x50600

    try:
        from PyQt5.Qt import QT_VERSION
    except ImportError:
        from PyQt5.QtCore import QT_VERSION

elif qt_config == 6:
    from PyQt6.QtCore import PYQT_VERSION
    from PyQt6.QtCore import QT_VERSION

    # Ensure resources from resources_rc are registered in PyQt6's resource system
    try:
        import resources_rc
        from PyQt6 import QtCore as _QtCore6
        _qt_v = [int(_v) for _v in _QtCore6.qVersion().split('.')]
        _rcc_v = 1 if _qt_v < [5, 8, 0] else 2
        _struct = resources_rc.qt_resource_struct_v1 if _rcc_v == 1 else resources_rc.qt_resource_struct_v2
        _QtCore6.qRegisterResourceData(_rcc_v, _struct, resources_rc.qt_resource_name, resources_rc.qt_resource_data)
    except Exception:
        pass
