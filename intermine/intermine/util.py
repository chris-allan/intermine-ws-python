def openAnything(source):
    # Try to open with urllib (http, ftp, file url)
    import urllib
    try:
        return urllib.urlopen(source)
    except (IOError, OSError):
        pass

    try:
        return open(source)
    except (IOError, OSError):
        pass

    import StringIO
    return StringIO.StringIO(str(source))
