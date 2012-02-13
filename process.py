#!/usr/bin/python

# Convert a file or directory recursively from xpath expressions to css expressions
# Limitations: xxx

import cssify
import os, fnmatch, re, shutil
from optparse import OptionParser
from pwd import getpwnam
from grp import getgrnam

file_count = 0 # Number of .php files encountered when doing a replace
replace_count = 0 # Number of xpaths replaces with css
xpath_skip_count = 0 # Number of xpaths skipped b/c it couldn't be processed or other reason

# Count xpaths
def xpath_count(path):
   
    count = 0
    if os.path.isdir(path):
        for path, dirs, files in os.walk(os.path.abspath(path)):
            for filename in files:
                filepath = os.path.join(path, filename)
                count = count + xpath_count(filepath)
        return count

    f = open(path)
    s = f.read()
    f.close()

    # simplified regex - single or double-quote followed by xpath= or //
    regex = r'(\'|")(xpath=|\/\/)'
    return len(re.findall(regex, s))

# Replace all occurences of xpaths with css equivalent in file
# This method is conservative.  It does not replace the following:
#     - xpath locators inside getXpathCount()
#     - xpath locators that are assigned to variables
#     - xpath locators that contain variables ($)
def replace(path):

    print("*** {0} ***".format(path))

    # If this is a directory, look for files/directories w/i it
    if os.path.isdir(path):

        print("  processing directory")
        for path, dirs, files in os.walk(os.path.abspath(path)):
            for filename in files:
                filepath = os.path.join(path, filename)
                replace(filepath)
        
        return

    # Not a directory
    filepath = path

    # Reject non-PHP files
    if filepath[-4:] != '.php':
        print("  skipping '{0}' - not PHP file".format(filepath))
        return 

    global file_count
    file_count = file_count + 1

    # uid and gid for chown below
    uid = getpwnam('intserver')[2]
    gid = getgrnam('integration')[2]

    # Read file
    f = open(filepath)
    s = f.read()
    f.close()

    # Write to backup file
    backup_filepath = "{0}.bak".format(filepath)
    f = open(backup_filepath, 'w')
    f.write(s)
    f.close()

    os.chown(backup_filepath, uid, gid)


    # Find occurences of xpath and replace with css locators
    # double-quotes
    #regex = r'(\w+)\("(\/\/[^\\"\$]+)"\)' # double quotes
    #delimiter = '"'
    #s = re.sub(regex, lambda m: xpath_replace(m, delimiter), s)

    # single-quotes
    #regex = r"(\w+)\('(\/\/[^\\'\$]+)'\)" # single quotes
    #delimiter = "'"
    #s = re.sub(regex, lambda m: xpath_replace(m, delimiter), s)

    # someMethod("//some/path"), someMethod('//some/path'), someMethod("//some[contains(@class, \"stuff\")]")
    regex = r'(\w+)\((\'|")((xpath=|\/\/)[^\3]+)\3\)'
    s = re.sub(regex, lambda m: xpath_replace_method(m.group(0), m.group(1), m.group(4), m.group(3)))

    # private properties
    regex = r'\$(_\S+) = (\'|")((xpath=|\/\/)[^\2\n]+)\2;'
    s = re.sub(regex, lambda m: xpath_replace_property(s, m.group(0), m.group(1), m.group(3), m.group(2)
    #matches = re.finditer(regex, s)
    #for m in matches:
    #    property = m.group(1)
    #    quote = m.group(2)
    #    xpath = m.group(3)
    # 
    #     print("Private property: {0} - {1}".format(property, xpath))
    #
    #    # Used in file using concatenation
    #    regex = re.compile("['|\"] . \$this->{0} . ['|\"]".format(property))
    #    cnt = len(re.findall(regex, s))
    #
    #    # Used in file inside double-quotes
    #    regex = re.compile('".*\$this->{0}.*"'.format(property))
    #    cnt = cnt + len(re.findall(regex, s))
    #
    #    # Assigned to another variable
    #    regex = re.compile('\$\S+ = \$this->{0};'.format(property))
    #    cnt = cnt + len(re.findall(regex, s))
    #
    #    #if cnt == 0:
    #    #
    #    #    xpath_replace(m, quote)

    f = open(filepath, 'w')
    f.write(s)
    f.close()

    os.chown(filepath, uid, gid)

# Replace xpath in property declaration
def replace_xpath_property(search_str, match_str, property, xpath, quote):
    """Replace xpath with css for a class property

    Replaces an xpath expression with with the equivalent css expression
    inside the match_str if the following is true:
    - The property is not used inside the search_str in concatenation
    - The property is not used inside the search_str inside double-quotes
    - The property is not assigned to another variable
    - The xpath can be converted to a css expression using cssify
    This method is intented to be a callback from re.sub

    Args:
        search_str: The original string that was searched
        match_str: The entire string that was matched
        property: The property name, e.g., _someProperty
        xpath: The xpath expression
        quote: The type of quoting used ' or "
    Returns:
        The original match_str or the match_str with the xpath expression
        replaced with the css expressions, if possible.
    """

    print("Private property: {0} - {1}".format(property, xpath))

    # Used in file using concatenation
    regex = re.compile("['|\"] . \$this->{0} . ['|\"]".format(property))
    if len(re.findall(regex, search_str)) > 0:
        return match_str

    # Used in file inside double-quotes
    regex = re.compile('".*\$this->{0}.*"'.format(property))
    if len(re.findall(regex, search_str)) > 0:
        return match_str

    # Assigned to another variable
    regex = re.compile('\$\S+ = \$this->{0};'.format(property))
    if len(re.findall(regex, search_str)) > 0:
        return match_str

    return xpath_to_css(xpath, quote)


def replace_xpath_method(match_str, method, xpath, quote):
    """Replace xpath with css for a method call

    Replaces an xpath expression with with the equivalent css expression
    inside the match_str if the following is true:
    - The method name is not getXpathCount()
    - The quote is single-quote OR double-quote with no variable inside
    This method is intented to be a callback from re.sub

    Args:
        match_str: The entire string that was matched
        method: The method name, e.g., click()
        xpath: The xpath expression
        quote: The type of quoting used ' or "
    Returns:
        The original match_str or the match_str with the xpath expression
        replaced with the css expressions, if possible.
    """

    # No replacement if getXpathCount or xpath contains a variable
    if method == 'getXpathCount' or (quote == '"' and xpath.find('$') != -1):

        return match_str

    else:

        return xpath_to_css(xpath, quote)


def xpath_to_css(xpath, quote):
    """Convert an xpath expression to a css expression
    
    Attempts xpath to css conversion, if fails, returns the xpath

    Args:
        xpath: xpath string
        quote: single or double-quote ' or "

    Returns:
        xpath converted to css, or xpath if conversion fails
    """

    try:
        css = cssify.cssify(xpath)
        print("'{0}' converted to '{1}".format(xpath, css))

        css = css.replace(quote, "\\{0}".format(quote)) # escape quote
        global replace_count
        replace_count = replace_count + 1

        return str.replace(xpath, "css={0}".format(css))

    except cssify.XpathException:
        print("Unable to convert xpath '{0}' to css expression".format(xpath))
        global xpath_skip_count
        xpath_skip_count = xpath_skip_count + 1
        return str    

    

# Replace xpath with css, use in replace() as an argument to re.sub()
def xpath_replace(m, delimiter):
    
    str = m.group(0) # Original string
    method = m.group(1) # Method part of match
    xpath = m.group(2) # xpath part of match

    # If method is getXpathCount(), return xpath
    if method == 'getXpathCount':
        return str

    # Attempt to convert, if successful, return string w/ xpath replaced by css, otherwise return original
    try:
        css = cssify.cssify(xpath)
        print("'{0}' converted to '{1}".format(xpath, css))

        css = css.replace(delimiter, "\\{0}".format(delimiter)) # escape delimiter
        global replace_count
        replace_count = replace_count + 1

        return str.replace(xpath, "css={0}".format(css))
    except cssify.XpathException:
        print("Unable to convert xpath '{0}' to css expression".format(xpath))
        global xpath_skip_count
        xpath_skip_count = xpath_skip_count + 1
        return str

# Restore backup files
def restore(path):        

    # Move backup files
    print("*** {0} ***".format(path))

    # If this is a directory, look for files/directories w/i it
    if os.path.isdir(path):

        print("  processing directory")
        for path, dirs, files in os.walk(os.path.abspath(path)):
            for filename in files:
                filepath = os.path.join(path, filename)
                restore(filepath)

        return

    filepath = path

    # Reject non-PHP files
    if filepath[-8:] != '.php.bak':
        print("  skipping '{0}' - not .bak.php file".format(filepath))
        return

    shutil.move(filepath, filepath[:-4])



if __name__ == "__main__":

    usage = "usage: %prog [options] filepath"
    parser = OptionParser(usage)
    parser.add_option("-r", "--restore",
                      action="store_true", dest="restore", default=False,
                      help="restore backup files")
    parser.add_option("-c", "--count",
                      action="store_true", dest="count", default=False,
                      help="print total count of xpaths")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("filepath is required")

    # Filepath is first argument after options
    path = args[0]

    # Decide what method to run based on arguments
    if options.restore:
        restore(path)
    elif options.count:
        cnt = xpath_count(path)
        print("Found {0} xpaths".format(cnt))
    else:
        replace(path)
        print("File count: {0}".format(file_count))
        print("Replace count: {0}".format(replace_count))
        print("Xpath skip count: {0}".format(xpath_skip_count))