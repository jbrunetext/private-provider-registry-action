from main import Registry

from os import path

rel = Registry()
rel.create_directory()


def test_tree_registry():
    """Test if the tree is OK """
    assert str(path.exists("registry")) == "True"


def test_tree_well_known():
    """Test well-known """
    assert str(path.exists("registry/.well-known")) == "True"
