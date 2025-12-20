# Plugin
 Class Widgets 2, with Plugin.

## Overview
In Class Widgets 2, we still use JSON as the format for the plugin manifest file.
And it usually called `cwplugin.json`

`id`: The unique identifier of the plugin.

`icon` (optional): The icon file path of the plugin.

`name`: The name of the plugin.

`version`: The version of the plugin. Like `1.0.0`.

`api_version`: The API version of the plugin. Like `>=1.0.0`, `*`,or `<=1.2.345.6` (Support PEP 440).

`description` (optional): The description of the plugin.

`entry`: The entry file path of the plugin.

`author`: The author of the plugin.

`url` (optional): The URL of the plugin repository. Like `https://github.com/owner/repo`.

`readme` (optional): The readme file path of the plugin.

### Plugin Manifest File
```json
{
  "id": "example.plugin.id",
  "icon": "example.png",
  "name": "Example Plugin",
  "version": "1.0.0",
  "api_version": "1.0.0",
  "description": "This is an example plugin.",
  "entry": "main.py",
  "author": "Your Name",
  "url": "https://github.com/owner/repo",
  "readme": "README.md"
}
```