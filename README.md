# WGGF Archive Util

Python script to download the monthly digests of the [WGGF](https://www.wggf.de).

```console
$ python wggf_archive_util.py --help
usage: wggf-monthly-digest.py [-h] -u USERNAME -p PASSWORD [-v] out_dir

Utility to scrape the mailing list archive of WGGF https://www.wggf.de.

positional arguments:
  out_dir               Directory to store the scraped data. Will be created, if non existent.

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Your member username you would usually use to authenticate.
  -p PASSWORD, --password PASSWORD
                        Your member password you would usually use to authenticate.
  -v, --verbose         Print verbose output.
```

Use your credentials you would usually use to authenticate to the WGGF's mailing list archive:

```console
$ python wggf_archive_util.py -u example@mail.com -p pw1234 /path/to/store/data
```

This will download all the monthly digests of the WGGF mailing list archive to the specified directory. You can further process the data with any tool of your choice.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
