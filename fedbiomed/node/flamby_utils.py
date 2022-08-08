from fedbiomed.common.constants import ErrorNumbers
from fedbiomed.common.exceptions import FedbiomedDatasetError
import flamby.datasets as fsets
import pkgutil

def get_flamby_datasets():
    """Get automatically dataset (dataset name and module name containing the federated class) from the flamby package.

    Returns:
        A tuple containing 2 elements :
            - the first is a dictionary with integers as keys (1 to X, X being the number of flamby datasets)
            and values being the absolute path of the package which contains the federated class of the dataset (e.g. flamby.datasets.fed_ixi)
            - the second is also a dictionary, with same keys as the first dictionary, and values being a short name identifying
            each dataset (e.g. 'ixi'), to display in the interface all the options of flamby datasets in a convenient way in the selection menu.

    """
    prefix = fsets.__name__ + "."
    available_flamby_datasets = {}
    for i, (importer, modname, ispkg) in enumerate(pkgutil.iter_modules(fsets.__path__, prefix), start=1):
        available_flamby_datasets[i] = modname
    valid_flamby_options = {i: val.split(".")[-1][4:] for i, val in available_flamby_datasets.items()}
    return available_flamby_datasets, valid_flamby_options


def get_key_from_value(my_dict: dict, val: str):
    """Get key from value of a particular dictionary, if the searched value is present in it.
    This function is used to get the index of a FLamby dataset, given a FLamby option selected through the interface (short name identifying each FLamby dataset).
    Then, the obtained index allows us to import the right package which contains the federated class (dataloader).

    Args:
        my_dict: dictionary
        val: value

    Returns:
        The key as a string if the value is found, or a string indicating that the key doesn't exist.
    """
    key_found = False
    for key, value in my_dict.items():
        if val == value:
            key_found = True
            return key

    if not key_found:
        raise FedbiomedDatasetError(f"{ErrorNumbers.FB614.value} Dictionary containing FLamby options should "
                                    f"contain the option selected through the Fed-BioMed interface. ")


def get_transform_compose_flamby(train_transform_flamby: list):
    """Function allowing to retrieve a Compose function to perform some transformation on a FLamby dataset.

    Args:
        train_transform_flamby: It has to be defined as a list containing two string elements:
        - the first is the imports needed to perform the transformation
        - the second is the Compose object that will be used to input the transform parameter of the FLamby dataset federated class
    
    Returns:
        A Compose object to input the transform parameter
    """
    for i, e in enumerate(train_transform_flamby):
        if i == 0:
            exec(e)
        if i == 1:
            transform_compose_flamby = eval(e)
    return transform_compose_flamby