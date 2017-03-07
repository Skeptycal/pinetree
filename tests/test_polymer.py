import unittest
import random
from pysinthe import feature, polymer


class TestPolymerMethods(unittest.TestCase):

    def setUp(self):
        promoter = feature.Promoter("promoter1",
                                    5,
                                    15,
                                    ["ecolipol", "rnapol"]
                                    )
        terminator = feature.Terminator("myterm",
                                        50,
                                        55,
                                        {"rnapol": {"efficiency": 1.0},
                                         "ecolipol": {"efficiency": 0.6}
                                         })
        mask = feature.Mask("mask",
                            10,
                            100,
                            ["ecolipol"])

        self.pol1 = feature.Polymerase("ecolipol",
                                       20,
                                       10,
                                       30,
                                       ["ecolipol", "terminator", "rnapol"]
                                       )
        self.pol2 = feature.Polymerase("rnapol",
                                       60,
                                       10,
                                       30,
                                       ["ecolipol", "terminator", "rnapol"]
                                       )
        self.pol3 = feature.Polymerase("rnapol",
                                       40,
                                       10,
                                       30,
                                       ["rnapol", "ecolipol", "rnapol"]
                                       )

        self.polymer = polymer.Polymer("mygenome",
                                       100,
                                       [promoter, terminator],
                                       mask)

        self.assertTrue(terminator.is_covered())
        self.assertTrue(promoter.is_covered())
        self.assertEqual(self.polymer.uncovered["promoter1"], 0)
        self.assertEqual(self.polymer.uncovered["myterm"], 0)
        self.fired = False
        self.polymer.propensity_signal.connect(self.fire)

    def fire(self):
        self.fired = True

    def test_bind_polymerase(self):
        random.seed(22)
        # Promoter should be covered and inaccessible
        self.assertRaises(RuntimeError,
                          self.polymer.bind_polymerase, self.pol1, "promoter1")
        # Shift mask back 10 positions
        for i in range(10):
            self.polymer.shift_mask()
        # Bind polymerase
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        # Check changes in coverings and positions
        self.assertEqual(self.pol1.start, 5)
        self.assertEqual(self.pol1.stop, 15)
        self.assertEqual(self.polymer.uncovered["promoter1"], 0)
        self.assertEqual(self.polymer.prop_sum, 30)
        self.assertTrue(self.fired)

    def test_execute(self):
        self.setUp()
        for i in range(100):
            self.polymer.shift_mask()
        # Arrange polymerases along polymer
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        for i in range(35):
            self.polymer._move_polymerase(self.pol1)
        self.polymer.bind_polymerase(self.pol2, "promoter1")
        for i in range(25):
            self.polymer._move_polymerase(self.pol2)
        self.polymer.bind_polymerase(self.pol3, "promoter1")

        for i in range(30):
            self.polymer.execute()

        # Once all of the polymerases have terminated, execute should throw
        # a RuntimeError
        with self.assertRaises(RuntimeError):
            for i in range(30):
                self.polymer.execute()

    def test_shift_mask(self):
        self.setUp()
        old_mask_start = self.polymer.mask.start
        self.polymer.shift_mask()
        self.assertEqual(old_mask_start + 1, self.polymer.mask.start)

        self.assertTrue(self.polymer.elements[0].is_covered())
        self.assertTrue(self.polymer.elements[1].is_covered())

        for i in range(10):
            self.polymer.shift_mask()

        self.assertFalse(self.polymer.elements[0].is_covered())
        self.assertTrue(self.polymer.elements[1].is_covered())

        for i in range(200):
            self.polymer.shift_mask()
        # Make sure mask can't get shifted beyond its end position
        self.assertEqual(self.polymer.mask.start, self.polymer.mask.stop)
        self.assertFalse(self.polymer.elements[1].is_covered())

    def test_terminate(self):
        self.setUp()
        for i in range(10):
            self.polymer.shift_mask()

        self.polymer.bind_polymerase(self.pol1, "promoter1")

        old_prop_sum = self.polymer.prop_sum
        self.polymer.terminate(self.pol1)

        self.assertNotEqual(self.polymer.prop_sum, old_prop_sum)
        self.assertTrue(self.fire)
        with self.assertRaises(ValueError):
            self.polymer.polymerases.index(self.pol1)

    def test_count_uncovered(self):
        # Check that cached count matches true count
        count = 0
        for element in self.polymer.elements:
            if element.name == "promoter1" and not element.is_covered():
                count += 1
        self.assertEqual(self.polymer.count_uncovered("promoter1"), count)

        count = 0
        for element in self.polymer.elements:
            if element.name == "myterm" and not element.is_covered():
                count += 1
        self.assertEqual(self.polymer.count_uncovered("myterm"), count)

    def test_calculate_propensity(self):
        prop_sum = 0
        for pol in self.polymer.polymerases:
            prop_sum += pol.speed
        self.assertEqual(prop_sum, self.polymer.calculate_propensity())

    def test_insert_polymerase(self):
        # Make sure we're starting with a fresh polymer
        self.setUp()

        self.polymer._insert_polymerase(self.pol2)
        self.assertEqual(self.polymer.polymerases.index(self.pol2), 0)

        self.polymer._insert_polymerase(self.pol1)
        self.assertEqual(self.polymer.polymerases.index(self.pol1), 0)
        self.assertEqual(self.polymer.polymerases.index(self.pol2), 1)

        self.polymer._insert_polymerase(self.pol3)
        self.assertEqual(self.polymer.polymerases.index(self.pol1), 0)
        self.assertEqual(self.polymer.polymerases.index(self.pol2), 2)
        self.assertEqual(self.polymer.polymerases.index(self.pol3), 1)

        # Trying to insert the same pol object twice should throw an error
        with self.assertRaises(RuntimeError):
            self.polymer._insert_polymerase(self.pol2)

    def test_choose_polymerase(self):
        # Start with clean polymer
        self.setUp()
        # There are no polymerases on the transcript so trying to randomly
        # choose a polymerase should throw an error
        with self.assertRaises(RuntimeError):
            self.polymer._choose_polymerase()
        # Move mask back
        for i in range(100):
            self.polymer.shift_mask()
        # Arrange polymerases along polymer
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        for i in range(35):
            self.polymer._move_polymerase(self.pol1)
        self.polymer.bind_polymerase(self.pol2, "promoter1")
        for i in range(25):
            self.polymer._move_polymerase(self.pol2)
        self.polymer.bind_polymerase(self.pol3, "promoter1")
        # Set seed and randomly select polymerases by propensity
        random.seed(13)
        self.assertEqual(self.polymer._choose_polymerase(), self.pol3)
        self.assertEqual(self.polymer._choose_polymerase(), self.pol2)
        self.assertEqual(self.polymer._choose_polymerase(), self.pol2)

    def test_move_polymerase(self):
        # Start with clean polymer
        self.setUp()
        # Shift mask back to expose promoter
        for i in range(10):
            self.polymer.shift_mask()
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        self.assertEqual(self.polymer.uncovered["promoter1"], 0)
        self.assertTrue(self.polymer.elements[0].is_covered())

        # Move polymerase 10 spaces and re-expose promoter
        for i in range(11):
            self.polymer._move_polymerase(self.pol1)
        self.assertEqual(self.polymer.uncovered["promoter1"], 1)
        self.assertFalse(self.polymer.elements[0].is_covered())
        # Make sure that the mask has also moved appropriately
        self.assertEqual(self.polymer.mask.start, self.pol1.stop + 1)

        # Check collisions between polymerases
        self.polymer.bind_polymerase(self.pol2, "promoter1")
        for i in range(15):
            self.polymer._move_polymerase(self.pol2)
        # One polymerase should not be able to pass another
        self.assertEqual(self.pol2.stop + 1, self.pol1.start)
        self.assertFalse(self.polymer.elements_intersect(self.pol1, self.pol2))

        # Remove pol1
        self.polymer.terminate(self.pol1)
        # Make sure that pol2 is unable to shift mask back
        old_mask_start = self.polymer.mask.start
        for i in range(20):
            self.polymer._move_polymerase(self.pol2)
        self.assertEqual(old_mask_start, self.polymer.mask.start)
        self.assertEqual(self.polymer.mask.start, self.pol2.stop + 1)

        # Move back mask to expose terminator
        for i in range(60):
            self.polymer.shift_mask()
        self.assertFalse(self.polymer.elements[1].is_covered())
        self.assertTrue(self.pol2 in self.polymer.polymerases)
        # Test termination, pol should detach as soon as it hits terminator
        for i in range(24):
            self.polymer._move_polymerase(self.pol2)
        self.assertTrue(
            self.polymer.elements_intersect(self.pol2,
                                            self.polymer.elements[1])
            )
        self.assertFalse(self.pol2.attached)
        with self.assertRaises(ValueError):
            self.polymer.polymerases.index(self.pol2)

        # Now check for readthrough
        self.pol1.attached = True
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        random.seed(19)
        for i in range(42):
            self.polymer._move_polymerase(self.pol1)
        self.assertTrue(self.polymer.elements[1].readthrough)
        # Move and remove polymerase
        for i in range(20):
            self.polymer._move_polymerase(self.pol1)
        self.polymer.terminate(self.pol1)
        # Run polymerase through terminator again, this time it should terminate
        self.pol1.attached = True
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        for i in range(35):
            self.polymer._move_polymerase(self.pol1)
        self.assertFalse(self.polymer.elements[1].readthrough)
        self.assertFalse(self.pol1.attached)

    def test_resolve_mask_collisions(self):
        self.setUp()
        for i in range(10):
            self.polymer.shift_mask()
        # This polymerase is capable of shifting mask backwards
        self.polymer.bind_polymerase(self.pol1, "promoter1")
        self.pol1.start += 5
        self.pol1.stop += 5
        old_mask_start = self.polymer.mask.start
        self.assertFalse(self.polymer._resolve_mask_collisions(self.pol1))
        self.assertEqual(self.polymer.mask.start, old_mask_start + 1)
        # The polymerase and mask should never overlap by more than 1 position
        self.pol1.start += 5
        self.pol1.stop += 5
        with self.assertRaises(RuntimeError):
            self.polymer._resolve_mask_collisions(self.pol1)

        self.setUp()
        for i in range(10):
            self.polymer.shift_mask()
        self.polymer.bind_polymerase(self.pol2, "promoter1")
        old_mask_start = self.polymer.mask.start
        old_start = self.pol2.start
        old_stop = self.pol2.stop
        self.pol2.start += 5
        self.pol2.stop += 5
        self.assertTrue(self.polymer._resolve_mask_collisions(self.pol2))
        self.assertEqual(self.pol2.start, old_start + 4)
        self.assertEqual(self.pol2.stop, old_stop + 4)
        self.assertEqual(self.polymer.mask.start, old_mask_start)

    def test_resolve_collisions(self):
        pass

    def test_check_state(self):
        pass
