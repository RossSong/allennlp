# pylint: disable=no-self-use, invalid-name
import logging

import numpy
import pytest
import pyhocon
import torch
from torch.autograd import Variable

from allennlp.nn import InitializerApplicator
from allennlp.nn.initializers import block_orthogonal
from allennlp.common.checks import ConfigurationError
from allennlp.common.testing import AllenNlpTestCase
from allennlp.common.params import Params

class TestInitializers(AllenNlpTestCase):
    def setUp(self):
        super(TestInitializers, self).setUp()
        logging.getLogger('allennlp.nn.initializers').disabled = False

    def tearDown(self):
        super(TestInitializers, self).tearDown()
        logging.getLogger('allennlp.nn.initializers').disabled = True

    def test_regex_matches_are_initialized_correctly(self):
        class Net(torch.nn.Module):
            def __init__(self):
                super(Net, self).__init__()
                self.linear_1_with_funky_name = torch.nn.Linear(5, 10)
                self.linear_2 = torch.nn.Linear(10, 5)
                self.conv = torch.nn.Conv1d(5, 5, 5)

            def forward(self, inputs):  # pylint: disable=arguments-differ
                pass

        # pyhocon does funny things if there's a . in a key.  This test makes sure that we
        # handle these kinds of regexes correctly.
        json_params = """{"initializer": [
        ["conv", {"type": "constant", "val": 5}],
        ["funky_na.*bi", {"type": "constant", "val": 7}]
        ]}
        """
        params = Params(pyhocon.ConfigFactory.parse_string(json_params))
        initializers = InitializerApplicator.from_params(params['initializer'])
        model = Net()
        initializers(model)

        for parameter in model.conv.parameters():
            assert torch.equal(parameter.data, torch.ones(parameter.size()) * 5)

        parameter = model.linear_1_with_funky_name.bias
        assert torch.equal(parameter.data, torch.ones(parameter.size()) * 7)

    def test_block_orthogonal_can_initialize(self):
        tensor = Variable(torch.zeros([10, 6]))
        block_orthogonal(tensor, [5, 3])
        tensor = tensor.data.numpy()

        def test_block_is_orthogonal(block) -> None:
            matrix_product = block.T @ block
            numpy.testing.assert_array_almost_equal(matrix_product,
                                                    numpy.eye(matrix_product.shape[-1]), 6)
        test_block_is_orthogonal(tensor[:5, :3])
        test_block_is_orthogonal(tensor[:5, 3:])
        test_block_is_orthogonal(tensor[5:, 3:])
        test_block_is_orthogonal(tensor[5:, :3])

    def test_block_orthogonal_raises_on_mismatching_dimensions(self):
        tensor = torch.zeros([10, 6, 8])
        with pytest.raises(ConfigurationError):
            block_orthogonal(tensor, [7, 2, 1])
