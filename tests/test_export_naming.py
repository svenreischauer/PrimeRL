import unittest

from primerl.export_naming import OligoRow, build_order_oligos, order_pair_tag


class OrderTagTests(unittest.TestCase):
    def test_qpcr_tag(self) -> None:
        self.assertEqual(order_pair_tag("qpcr", 2), "qRT2")

    def test_seq_tag(self) -> None:
        self.assertEqual(order_pair_tag("seq", 3), "seq3")

    def test_default_numeric_tag(self) -> None:
        self.assertEqual(order_pair_tag("pd", 4), "4")


class BuildOrderOligoTests(unittest.TestCase):
    def test_qpcr_includes_forward_and_reverse(self) -> None:
        rows = build_order_oligos(
            page="qpcr",
            selected_pairs=[("ACGT", "TGCA")],
            gene="ACTB",
        )
        self.assertEqual(
            rows,
            [
                OligoRow("ACTB_qRT1F", "ACGT", 4),
                OligoRow("ACTB_qRT1R", "TGCA", 4),
            ],
        )

    def test_seq_only_includes_forward(self) -> None:
        rows = build_order_oligos(
            page="seq",
            selected_pairs=[("AAAA", "TTTT"), ("CCCC", "GGGG")],
            gene="GENE1",
        )
        self.assertEqual(
            rows,
            [
                OligoRow("GENE1_seq1F", "AAAA", 4),
                OligoRow("GENE1_seq2F", "CCCC", 4),
            ],
        )

    def test_non_seq_skips_reverse_if_empty(self) -> None:
        rows = build_order_oligos(
            page="qpcr",
            selected_pairs=[("ATAT", "")],
            gene="MYC",
        )
        self.assertEqual(rows, [OligoRow("MYC_qRT1F", "ATAT", 4)])


if __name__ == "__main__":
    unittest.main()

