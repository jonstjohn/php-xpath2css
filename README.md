# Xpath to CSS Converter for PHP Files

This python module is designed to safely convert xpath expressions in PHP files to their equivalent CSS expression.  This was originally designed to work with the Selenium web testing framework, particularly in PHPUnit, although it could be used for other applications.  It utilizes the cssify library (bundled within the code) created by Santiago Suarez Ordoñez (santiycr) which handles the actual conversion from xpath to css.

The module can be executed with a file or directory path as a single argument, and will safely convert xpath expressions, ignoring certain situations where conversion may not work properly.  By default, the script backs up the original file in the same directory using a '.bak' suffix to the original file name.  Files can be reverted using the -r switch will will copy the .bak file back to the original and delete it.
