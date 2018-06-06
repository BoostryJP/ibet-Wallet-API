def wait_all_futures(fs):
    for f in fs:
        f.result()
