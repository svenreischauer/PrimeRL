import unittest

from primerl.io_fasta import read_first_fasta_sequence


class FastaIoTests(unittest.TestCase):
    def test_read_first_sequence(self) -> None:
        text = ">seq1\nACGT\nTTAA\n>seq2\nGGGG\n"
        self.assertEqual(read_first_fasta_sequence(text), "ACGTTTAA")

    def test_empty(self) -> None:
        self.assertEqual(read_first_fasta_sequence(""), "")


if __name__ == "__main__":
    unittest.main()

