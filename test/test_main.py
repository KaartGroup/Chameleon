import unittest
# from pathlib import Path

from src.main import Worker

# TEST_FOLDER = Path("test")


class TestBuildQuery(unittest.TestCase):
    # def __init__(self):
    #     super().__init__()

    def setUp(self):
        self.files = {
            "old": "test/old.csv",
            "new": "test/new.csv",
            "output": "test/output"
        }
        self.gold_sql = (
            "SELECT (substr(ifnull(new.\"@type\",old.\"@type\"),1,1) || ifnull(new.\"@id\",old.\"@id\")) AS id, "
            "('http://localhost:8111/load_object?new_layer=true&objects=' || substr(ifnull(new.\"@type\","
            "old.\"@type\"),1,1) || ifnull(new.\"@id\",old.\"@id\")) AS url, "
            "ifnull(new.\"@user\",old.\"@user\") AS user, substr(ifnull(new.\"@timestamp\","
            "old.\"@timestamp\"),1,10) AS timestamp, "
            "ifnull(new.\"@version\",old.\"@version\") AS version, "
            "ifnull(new.highway,old.highway) AS highway, "
            "ifnull(old.name,'') AS old_name, ifnull(new.name,'') AS new_name, "
            "CASE WHEN new.\"@id\" LIKE old.\"@id\" THEN \"modified\" ELSE \"deleted\" END \"action\" , "
            "NULL AS \"notes\" "
            f"FROM {self.files['old']} AS old LEFT OUTER JOIN {self.files['new']} AS new ON old.\"@id\" = new.\"@id\" "
            "WHERE old_name NOT LIKE new_name "
            "UNION ALL SELECT (substr(new.\"@type\",1,1) || new.\"@id\") AS id, "
            "('http://localhost:8111/load_object?new_layer=true&objects=' || substr(new.\"@type\",1,1) || new.\"@id\") AS url, "
            "new.\"@user\" AS user, substr(new.\"@timestamp\",1,10) AS timestamp, "
            "new.\"@version\" AS version, new.highway AS highway, "
            "ifnull(old.name,'') AS old_name, ifnull(new.name,'') AS new_name, "
            "\"new\" AS \"action\" , NULL AS \"notes\" "
            f"FROM {self.files['new']} AS new LEFT OUTER JOIN {self.files['old']} AS old ON new.\"@id\" = old.\"@id\" "
            "WHERE old.\"@id\" IS NULL AND length(ifnull(new_name,'')) > 0"
        )
        self.file_name = self.files["output"] + "_name.csv"
        self.func = Worker("name", self.files, False)

    def test_build_query_ungrouped(self):
        # print(gold_sql)
        test_sql = self.func.build_query("name", self.files, False)
        # print(test_sql)
        self.assertEqual(test_sql, self.gold_sql)

    def test_write_file_ungrouped(self):
        self.func.write_file(self.gold_sql, self.file_name)
        with open(self.file_name, "r") as f:
            test_file = f.read()
        with open("test/test_name.csv", "r") as f:
            gold_file = f.read()
        self.assertMultiLineEqual(test_file, gold_file)

    # from main import MainApp

    # sample test

    # def add(num1, num2):
    # 	return num1 + num2

    # def test_add():
    # 	assert add(2, 2) == 4


if __name__ == '__main__':
    unittest.main()
