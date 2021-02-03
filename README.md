# Subrawtica
Command line application that recursively scrapes the Subnautica Wiki to break down any item into its raw materials.

### Install requirements
```pip install requests && pip install beautifulsoup4￼```

### Run
```python3 subrawtica.py```

The application continues to prompt the user until a keyboard interrupt (Control-C) or an empty input.


### Known Issues
* It's a little slow before you have common items cached.
  * Scraping dozens of pages is not the fastest way to do this, but it will still be accurate after game updates.
