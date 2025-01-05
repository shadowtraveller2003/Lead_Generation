import csv
import os.path

class CsvWriter:
    def __init__(self, filename: str, fieldnames: list[str]) -> None:
        self.filename = filename
        self.fieldnames = fieldnames

        if not os.path.exists(filename):
            self._init()

    def _init(self) -> None:
        with open(self.filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def append(self, data: list[dict]) -> None:
        # Debugging: Ensure data is a list of dictionaries
        #print(f"Data to append: {data}")
        #print(f"Type of data: {type(data)}")
        if data:
            print("")
            #print(f"Type of first element in data: {type(data[0])}")

        with open(self.filename, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            for d in data:
                if isinstance(d, dict):
                    writer.writerow(d)
                else:
                    print("")
                    #print(f"Skipping entry as it's not a dictionary: {d}")
