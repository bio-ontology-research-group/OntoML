from unittest import TestCase

import mowl
mowl.init_jvm("10g")
from mowl.walking.walking import WalkingModel

class TestBaseClass(TestCase):

    def test_walk_method_raises_exception(self):
        """This checks if NotImplementedError is raised by walk method"""

        walker = WalkingModel(10, 5, "/tmp/outfile")
        self.assertRaises(NotImplementedError, walker.walk, [])