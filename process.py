#!/usr/bin/python

# Convert a file or directory recursively from xpath expressions to css expressions
# Limitations: xxx

import cssify
import os, re, shutil
from optparse import OptionParser

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
def replace_all(path):

    print("*** {0} ***".format(path))

    # If this is a directory, look for files/directories w/i it
    if os.path.isdir(path):

        print("  processing directory")
        for path, dirs, files in os.walk(os.path.abspath(path)):
            for filename in files:
                filepath = os.path.join(path, filename)
                replace_all(filepath)
        
        return

    # Not a directory
    filepath = path

    # Reject non-PHP files
    if filepath[-4:] != '.php':
        print("  skipping '{0}' - not PHP file".format(filepath))
        return 

    global file_count
    file_count = file_count + 1

    # Read file
    f = open(filepath)
    s = f.read()
    f.close()

    # Write to backup file
    backup_filepath = "{0}.bak".format(filepath)
    f = open(backup_filepath, 'w')
    f.write(s)
    f.close()

    # someMethod("//some/path"), someMethod('//some/path'), someMethod("//some[contains(@class, \"stuff\")]")
    regex = r'(\w+)\((\'|")((xpath=|\/\/)[^\2\n]+)\2(\)|,)'
    print("**** COUNT: {0}".format(len(re.findall(regex, s))))
    s = re.sub(regex, lambda m: xpath_replace_method(m.group(0), m.group(1), m.group(3), m.group(2)), s)

    # private properties
    regex = r'\$(_\S+) = (\'|")((xpath=|\/\/)[^\2\n]+)\2;'
    s = re.sub(regex, lambda m: xpath_replace_property(s, m.group(0), m.group(1), m.group(3), m.group(2)), s)

    # Variables - e.g., $xpath = '//table'
    regex = r'(\$\S+) = (\'|")((xpath=|\/\/)[^\2\n\$]+)\2;'
    s = re.sub(regex, lambda m: xpath_replace_variable(s, m.group(0), m.group(1), m.group(3), m.group(2)), s)

    f = open(filepath, 'w')
    f.write(s)
    f.close()

# Replace xpath in variable
def xpath_replace_variable(search_str, match_str, variable, xpath, quote):

    global xpath_skip_count

    print("Variable: {0} - {1}".format(variable, xpath))

    # Do not replace if variable is used w/i double-quotes
    regex = re.compile('".*\{0}.*"'.format(variable))
    if re.search(regex, search_str):
        print("  {0} used in variable assignment, skipping")
        xpath_skip_count += 1
        return match_str

    # Used in string concatenation
    if re.search(r'\.\s?\{0}'.format(variable), search_str) or re.search(r'\{0}\s?\.'.format(variable), search_str):
        print("  {0} used in concatenation")
        xpath_skip_count += 1
        return match_str

    return match_str.replace(xpath, xpath_to_css(xpath, quote))

# Replace xpath in property declaration
def xpath_replace_property(search_str, match_str, property, xpath, quote):
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

    global xpath_skip_count

    print("Private property: {0} - {1}".format(property, xpath))

    # Used in file using concatenation
    regex = re.compile("['|\"] . \$this->{0} . ['|\"]".format(property))
    if len(re.findall(regex, search_str)) > 0:
        xpath_skip_count += 1
        return match_str

    # Used in file inside double-quotes
    regex = re.compile('".*\$this->{0}.*"'.format(property))
    if len(re.findall(regex, search_str)) > 0:
        xpath_skip_count += 1
        return match_str

    # Assigned to another variable
    regex = re.compile('\$\S+ = \$this->{0};'.format(property))
    if len(re.findall(regex, search_str)) > 0:
        xpath_skip_count += 1
        return match_str

    return match_str.replace(xpath, xpath_to_css(xpath, quote))


def xpath_replace_method(match_str, method, xpath, quote):
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

    global xpath_skip_count

    # No replacement if getXpathCount or xpath contains a variable
    if method == 'getXpathCount' or (quote == '"' and xpath.find('$') != -1):

        xpath_skip_count += 1
        return match_str

    else:

        return "{0}->({1}{2}{3})".format(method, quote, xpath_to_css(xpath, quote), quote)


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
        replace_count += 1

        return "css={0}".format(css)

    except cssify.XpathException:
        print("Unable to convert xpath '{0}' to css expression".format(xpath))
        global xpath_skip_count
        xpath_skip_count += 1
        return xpath

    

# Replace xpath with css, use in replace() as an argument to re.sub()
def xpath_replace(m, delimiter):
    
    s = m.group(0) # Original string
    method = m.group(1) # Method part of match
    xpath = m.group(2) # xpath part of match

    # If method is getXpathCount(), return xpath
    if method == 'getXpathCount':
        return s

    # Attempt to convert, if successful, return string w/ xpath replaced by css, otherwise return original
    try:
        css = cssify.cssify(xpath)
        print("'{0}' converted to '{1}".format(xpath, css))

        css = css.replace(delimiter, "\\{0}".format(delimiter)) # escape delimiter
        global replace_count
        replace_count = replace_count + 1

        return s.replace(xpath, "css={0}".format(css))
    except cssify.XpathException:
        print("Unable to convert xpath '{0}' to css expression".format(xpath))
        global xpath_skip_count
        xpath_skip_count = xpath_skip_count + 1
        return s

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
    #parse.add_option("-n", "--no-backup"
    #    action="store_true", dest="no_backup", default=False,
    #    help="do not backup files)

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("filepath is required")

    # Filepath is first argument after options
    path = args[0]

    # Decide what method to run based on arguments
    if options.restore:
        restore(path)
    else:
        xpath_count = xpath_count(path)
        if options.count:
            print("Found {0} xpaths".format(xpath_count))
        if not options.count:
            replace_all(path)
            print("Xpath count: {0}".format(xpath_count))
            print("File count: {0}".format(file_count))
            print("Replace count: {0}".format(replace_count))
            print("Xpath skip count: {0}".format(xpath_skip_count))
