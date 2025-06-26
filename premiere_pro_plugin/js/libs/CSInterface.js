/**************************************************************************************************
*
* ADOBE CONFIDENTIAL
* ___________________
*
* Copyright 2013-2018 Adobe
* All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe and its suppliers, if any. The intellectual
* and technical concepts contained herein are proprietary to Adobe
* and its suppliers and are protected by all applicable intellectual
* property laws, including trade secret and copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe.
*
**************************************************************************************************/

/**
 * @class CSInterface
 * The CSInterface is the host application's interface to the extension.
 * It is a singleton object, and can be accessed directly.
 * <br>
 * The CSInterface provides the following functionalities:
 * <ul>
 * <li>It allows the extension to access information about the host application, such as the application name, version, and color theme.</li>
 * <li>It allows the extension to register for and receive event notifications from the host application.</li>
 * <li>It allows the extension to evaluate ExtendScript in the host application and to receive the result.</li>
 * <li>It provides a way to launch a URL in the default browser.</li>
 * <li>It provides a way to manage extension life-cycle.</li>
 * </ul>
 * <br>
 * All the methods in the CSInterface are asynchronous.
 * When a method has a return value, the value is returned through a callback function.
 *
 * @hideconstructor
 */
function CSInterface()
{
}

/**
 * The version of the CSInterface library.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getCurrentApiVersion = function()
{
	return "11.0.0";
};

/**
 * The host environment data object.
 *
 * @type {HostEnvironment}
 * @readonly
 */
CSInterface.prototype.getHostEnvironment = function()
{
	var result = window.__adobe_cep__.getHostEnvironment();
	return JSON.parse(result);
};


/**
 * The host application's localization.
 * For example, in English (US) on Windows, the value is "en_US".
 * In French on Macintosh, the value is "fr_FR".
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getHostLocale = function()
{
	return window.__adobe_cep__.getHostLocale();
};

/**
 * All available host applications's localizations.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getAvailableHostLocale = function()
{
    var result = window.__adobe_cep__.getAvailableHostLocale();
    return JSON.parse(result);
};

/**
 * The context in which this extension is running.
 * This can be a panel, a modal dialog, a modeless dialog, or an invisible extension.
 * The possible values are defined in the `CSEvent` class.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getRunningContext = function()
{
	return window.__adobe_cep__.getRunningContext();
};

/**
 * The unique identifier of this extension.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getExtensionId = function()
{
	return window.__adobe_cep__.getExtensionId();
};

/**
 * Retrieves the unique identifier of the host application.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getHostId = function()
{
	var env = this.getHostEnvironment();
	return env.appName;
};

/**
 * Closes this extension.
 * Does not unload the extension, which returns to the opening screen.
 * To unload the extension, see `closeExtension()`.
 */
CSInterface.prototype.close = function()
{
	window.__adobe_cep__.close();
};

/**
 * Unloads this extension.
 * To close the extension without unloading, see `close()`.
 */
CSInterface.prototype.closeExtension = function()
{
	window.__adobe_cep__.closeExtension();
};


/**
 * Retrieves the extension's context menu.
 * To use the context menu, you must define it in the extension manifest.
 *
 * @param {string} menuId - The unique identifier for the menu in the manifest.
 * @param {function} [menuCallback] - A function to call when the menu is ready.
 *
 */
CSInterface.prototype.setContextMenu = function(menuId, menuCallback)
{
	var menu = new Menu(menuId, menuCallback);
};

/**
 * Sets the context menu for an extension.
 * The menu is specified as an XML string.
 *
 * @param {string} menu - The XML string that defines the menu.
 * @param {function} [callback] - A function to call when the menu is ready.
 */
CSInterface.prototype.setContextMenuByXML = function(menu, callback)
{
	window.__adobe_cep__.invokeSync("setContextMenuByXML", menu, callback);
};

/**
 * Gets the context menu for an extension.
 *
 * @param {string} menuId - The unique identifier for the menu in the manifest.
 * @param {function} [callback] - A callback function that receives the menu XML as a string.
 */
CSInterface.prototype.getContextMenu = function(menuId, callback)
{
	window.__adobe_cep__.invokeAsync("getContextMenu", menuId, callback);
};

/**
 * Sets the flyout menu for a panel extension.
 * The menu is specified as an XML string.
 *
 * @param {string} menu - The XML string that defines the menu.
 */
CSInterface.prototype.setPanelFlyoutMenu = function(menu)
{
	window.__adobe_cep__.invokeSync("setPanelFlyoutMenu", menu);
};

/**
 * Shows or hides the title bar of the extension window.
 *
 * @param {boolean} [show=true] - Pass false to hide the title bar, true to show it.
 */
CSInterface.prototype.showWindowTitle = function(show)
{
	window.__adobe_cep__.invokeSync("showWindowTitle", (show === false) ? "false" : "true");
};

/**
 * Evaluates a JavaScript script in the host application.
 *
 * @param {string} script - The script to evaluate.
 * @param {function} [callback] - A callback function that receives the result of the script evaluation.
 *                                If the script returns a value, it is passed as a string.
 */
CSInterface.prototype.evalScript = function(script, callback)
{
	if(callback === null || callback === undefined)
	{
		callback = function(result){};
	}
	window.__adobe_cep__.evalScript(script, callback);
};


/**
 * Registers a callback function to handle an event of a given type, sent by the host application.
 * Your callback function should not perform any complex operations. It should be used only
 * to receive the event and delegate the work to other functions.
 * <br>
 * An event object of type `CSEvent` is passed to the callback function.
 * This object contains a `data` property, which contains any data associated with the event.
 * If the event is a scope-changed event, such as a new document being opened, the data object
 * contains a `scope` property, which specifies the new scope.
 * <br>
 * You can register more than one callback for an event. The order in which the callbacks are
 * invoked is not guaranteed to be the same as the order in which they were registered.
 * <br>
 * For a list of event types, see the `CSEvent` class description.
 *
 * @param {string} type - The type of event to listen for.
 * @param {function} listener - The callback function that handles the event.
 * @param {object} [obj] - An object that contains the context of the listener function.
 *
 * @see CSEvent
 * @see #removeEventListener()
 */
CSInterface.prototype.addEventListener = function(type, listener, obj)
{
	window.__adobe_cep__.addEventListener(type, listener, obj);
};

/**
 * Removes an event listener that has been registered for an event of a given type.
 *
 * @param {string} type - The type of event.
 * @param {function} listener - The callback function that was registered to handle the event.
 * @param {object} [obj] - An object that contains the context of the listener function.
 *
 * @see #addEventListener()
 */
CSInterface.prototype.removeEventListener = function(type, listener, obj)
{
	window.__adobe_cep__.removeEventListener(type, listener, obj);
};

/**
 * Dispatches an event of a given type to the host application.
 *
 * @param {CSEvent} event - The event to dispatch.
 *
 * @see CSEvent
 */
CSInterface.prototype.dispatchEvent = function(event)
{
	window.__adobe_cep__.dispatchEvent(event);
};

/**
 * Retrieves the full path of this extension.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getSystemPath = function(pathType)
{
	var path = decodeURI(window.__adobe_cep__.getSystemPath(pathType));
	var OSVersion = this.getOSInformation();
	if (OSVersion.indexOf("Mac") >= 0)
	{
		var prePath = "/";
		if (path.indexOf(prePath) === 0)
		{
			return path;
		}
		else
		{
			return prePath + path;
		}
	}
	else
	{
		return path;
	}
};

/**
 * Retrieves the version of the host application.
 * The format of version is separated by dots, such as "13.0.0".
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getHostVersion = function()
{
	var env = this.getHostEnvironment();
	return env.appVersion;
};

/**

 * Retrieves the user data folder for this extension.
 * This folder is not deleted when the extension is uninstalled.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getSystemPath = function(pathType)
{
	return window.__adobe_cep__.getSystemPath(pathType);
};

/**
 * Launches a URL in the default browser.
 * The URL must use the HTTP or HTTPS protocol. For example:
 * <pre>csInterface.openURLInDefaultBrowser("https://www.adobe.com");</pre>
 *
 * @param {string} url - The URL to launch.
 */
CSInterface.prototype.openURLInDefaultBrowser = function(url)
{
	window.__adobe_cep__.openURLInDefaultBrowser(url);
};


/**
 * Retrieves the operating system information.
 *
 * For example, "Mac OS X 10.13.6" or "Windows 10".
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.getOSInformation = function()
{
	return window.__adobe_cep__.getOSInformation();
};

/**
 * Retrieves the capabilities of the host application.
 * This is an object containing the following properties:
 * <ul>
 *   <li>`EXTENDED_PANEL_MENU`: True if the panel supports the panel flyout menu.</li>
 *   <li>`EXTENDED_PANEL_ICONS`: True if the panel supports the panel icons.</li>
 *   <li>`DELEGATE_APE`: True if the host application is running in APE mode.</li>
 * </ul>
 *
 * @type {object}
 * @readonly
 */
CSInterface.prototype.getHostCapabilities = function()
{
	var result = window.__adobe_cep__.getHostCapabilities();
	return JSON.parse(result);
};

/**
 * Sets a handler to be called when the extension window is resized.
 * Only one handler can be registered at a time. To remove a handler,
 * pass `null` for the `handler` parameter.
 *
 * @param {function|null} handler - The function that handles the resize event.
 *                           It is passed two arguments, the new width and height.
 */
CSInterface.prototype.resizeContent = function(handler)
{
	window.__adobe_cep__.resizeContent(handler);
};


/**
 * Resizes the extension to the specified dimensions.
 *
 * @param {number} width - The new width.
 * @param {number} height - The new height.
 */
CSInterface.prototype.resize = function(width, height)
{
	window.__adobe_cep__.resize(width, height);
};

/**
 * Registers an interest in a color theme change.
 * The callback function is invoked when the theme color of the host application changes.
 *
 * @param {string} interest - The color of interest. Pass one of these constants:
 * <ul>
 *   <li>`CSInterface.THEME_COLOR_CHANGED_EVENT`</li>
 *   <li>`CSInterface.THEME_BACKGROUND_COLOR`</li>
 *   <li>`CSInterface.THEME_HIGHLIGHT_COLOR`</li>
 * </ul>
 * @param {function} callback - The callback function that is invoked when the theme color changes.
 */
CSInterface.prototype.registerThemeColorInterest = function(interest, callback)
{
	//TODO: implement
};


/**
 * The event type for a change in the host application's theme color.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.THEME_COLOR_CHANGED_EVENT = "com.adobe.csxs.events.ThemeColorChanged";

/**
 * Constant for the theme background color type.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.THEME_BACKGROUND_COLOR = "background";

/**
 * Constant for the theme highlight color type.
 *
 * @type {string}
 * @readonly
 */
CSInterface.prototype.THEME_HIGHLIGHT_COLOR = "highlight";


/**
 * An object containing information about the host application's theme.
 * The object has these properties:
 * <ul>
 *    <li>`appBarBackgroundColor`</li>
 *    <li>`panelBackgroundColor`</li>
 *    <li>`lighterPanelBackgroundColor`</li>
 *    <li>`lightestPanelBackgroundColor`</li>
 *    <li>`fontColor`</li>
 *    <li>`lighterFontColor`</li>
 *    <li>`lightestFontColor`</li>
 *    <li>`appBarBackgroundColorSRGB`</li>
 *    <li>`panelBackgroundColorSRGB`</li>
 *    <li>`lighterPanelBackgroundColorSRGB`</li>
 *    <li>`lightestPanelBackgroundColorSRGB`</li>
 *    <li>`fontColorSRGB`</li>
 *    <li>`lighterFontColorSRGB`</li>
 *    <li>`lightestFontColorSRGB`</li>
 * </ul>
 * All color values are `RGBColor` objects.
 *
 * @type {object}
 * @readonly
 */
CSInterface.prototype.getThemeInformation = function()
{
	var theme = window.__adobe_cep__.getThemeInformation();
	return JSON.parse(theme);
};

/**
 * A color with red, green, blue, and alpha channels.
 *
 * @class RGBColor
 * @prop {number} red - The red channel, a value between 0 and 255.
 * @prop {number} green - The green channel, a value between 0 and 255.
 * @prop {number} blue - The blue channel, a value between 0 and 255.
 * @prop {number} alpha - The alpha channel, a value between 0 and 255.
 */


/**
 * An object that describes the host environment in which the extension is running.
 *
 * @class HostEnvironment
 * @prop {string} appName - The unique identifier of the host application.
 * @prop {string} appVersion - The version of the host application.
 * @prop {string} appLocale - The locale of the host application.
 * @prop {string} appUILocale - The UI locale of the host application.
 * @prop {string} appId - The unique identifier of the host application.
 * @prop {boolean} isDevMode - True if the host application is in developer mode.
 * @prop {SkinInfo} skinInfo - An object containing information about the application's theme colors.
 *
 * @see CSInterface.prototype.getHostEnvironment
 */

/**
 * @class CSEvent
 * A standard event object.
 *
 * @prop {string} type - The event type.
 * @prop {string} appId - The unique identifier of the application that generated the event.
 * @prop {string} extensionId - The unique identifier of the extension that generated the event.
 * @prop {object} data - Data associated with this event.
 *
 * @see CSInterface.prototype.addEventListener
 * @see CSInterface.prototype.dispatchEvent
 *
 * @hideconstructor
 */
function CSEvent(type, appId, extensionId)
{
	this.type = type;
	this.appId = appId;
	this.extensionId = extensionId;
	this.data = "";
}

var csInterface = new CSInterface();

/**
 * The `SystemPath` class, whose constants specify platform-specific paths to commonly used folders.
 * @class SystemPath
 */
var SystemPath = {
	/** The user's data folder. */
	USER_DATA : "userData",
	/** The user's common files folder. */
	COMMON_FILES : "commonFiles",
	/** The user's default document folder. */
	MY_DOCUMENTS : "myDocuments",
	/** The application's data folder. */
	APPLICATION_DATA : "applicationData",
	/** The host application's folder. */
	HOST_APPLICATION : "hostApplication",
    /** The extension folder. */
    EXTENSION: "extension",
    /** The user's data folder for all versions of the host application. */
    ALL_USERS_DATA: "allUsersData"
};

/**
 * Class `Menu`
 *
 * @class Menu
 * @prop {function} [menuCallback] - A function to call when the menu is ready.
 */
function Menu(menuId, menuCallback)
{
	this.menuId = menuId;
	this.menuCallback = menuCallback;
}

/**
 * Triggers the menu item in this menu.
 * @param {string} menuItemId
 *
 */
Menu.prototype.trigger = function(menuItemId)
{
	csInterface.invokeSync("triggerMenu", [this.menuId, menuItemId]);
}; 