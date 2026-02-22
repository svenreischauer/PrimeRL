import unittest

from primerl.ensembl_adapter import (
    EnsemblError,
    EnsemblNoGeneFound,
    build_lookup_symbol_url,
    choose_preferred_transcript,
    build_sequence_id_url,
    choose_longest_transcript,
    decode_ensembl_json,
    extract_transcript_choices,
    fetch_json_with_transport,
    map_ensembl_seq_type,
    normalize_species_name,
)


class UrlAndMappingTests(unittest.TestCase):
    def test_species_normalization(self) -> None:
        self.assertEqual(normalize_species_name("Homo sapiens"), "homo_sapiens")

    def test_seq_type_mapping(self) -> None:
        self.assertEqual(map_ensembl_seq_type("coding"), "cds")
        self.assertEqual(map_ensembl_seq_type("utr5"), "5utr")
        self.assertEqual(map_ensembl_seq_type("genomic"), "genomic")

    def test_lookup_url(self) -> None:
        u = build_lookup_symbol_url("Homo sapiens", "actb")
        self.assertIn("/lookup/symbol/homo_sapiens/actb", u)
        self.assertTrue(u.endswith("?expand=1"))

    def test_seq_url(self) -> None:
        u = build_sequence_id_url("ENST0001", "cdna")
        self.assertEqual(u, "https://rest.ensembl.org/sequence/id/ENST0001?type=cdna")


class DecodeAndFetchTests(unittest.TestCase):
    def test_decode_ok(self) -> None:
        ok, data, err = decode_ensembl_json('{"id":"X"}')
        self.assertTrue(ok)
        self.assertEqual(data["id"], "X")
        self.assertEqual(err, "")

    def test_decode_fail(self) -> None:
        ok, data, err = decode_ensembl_json('{"id":')
        self.assertFalse(ok)
        self.assertIsNone(data)
        self.assertTrue(len(err) > 0)

    def test_fetch_no_gene(self) -> None:
        def transport(_url: str) -> tuple[int, str]:
            return 22, "HTTP 400 not found"

        result = fetch_json_with_transport(
            "https://rest.ensembl.org/lookup/symbol/homo_sapiens/NOPE?expand=1",
            transport,
        )
        self.assertIsInstance(result, EnsemblNoGeneFound)

    def test_fetch_error(self) -> None:
        def transport(_url: str) -> tuple[int, str]:
            return 7, "connection failed"

        result = fetch_json_with_transport("https://rest.ensembl.org/sequence/id/X?type=cdna", transport)
        self.assertIsInstance(result, EnsemblError)

    def test_fetch_parse_error(self) -> None:
        def transport(_url: str) -> tuple[int, str]:
            return 0, '{"id":'

        result = fetch_json_with_transport("https://rest.ensembl.org/sequence/id/X?type=cdna", transport)
        self.assertIsInstance(result, EnsemblError)
        self.assertIn("Unable to parse Ensembl response", result.message)

    def test_fetch_success(self) -> None:
        def transport(_url: str) -> tuple[int, str]:
            return 0, '{"id":"ENSG1","Transcript":[]}'

        result = fetch_json_with_transport("https://rest.ensembl.org/lookup/symbol/homo_sapiens/ACTB?expand=1", transport)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "ENSG1")


class TranscriptChoiceTests(unittest.TestCase):
    def test_extract_and_choose_longest(self) -> None:
        payload = {
            "Transcript": [
                {"id": "ENST2", "display_name": "tx2", "length": 1200},
                {"id": "ENST1", "display_name": "tx1", "Translation": {"length": 1300}},
                {"id": "ENST3", "display_name": "tx3", "start": 10, "end": 300},
            ]
        }
        choices = extract_transcript_choices(payload)
        self.assertEqual(len(choices), 3)
        best = choose_longest_transcript(choices)
        self.assertIsNotNone(best)
        self.assertEqual(best.transcript_id, "ENST1")

    def test_choose_preferred_transcript_prioritizes_canonical_and_quality(self) -> None:
        payload = {
            "Transcript": [
                {
                    "id": "ENST_LONG",
                    "display_name": "long_noncanonical",
                    "length": 3000,
                    "biotype": "protein_coding",
                    "is_canonical": 0,
                    "transcript_support_level": 1,
                    "appris": "principal1",
                    "Translation": {"length": 1000},
                },
                {
                    "id": "ENST_CANON",
                    "display_name": "canonical",
                    "length": 2200,
                    "biotype": "protein_coding",
                    "is_canonical": 1,
                    "transcript_support_level": 1,
                    "appris": "principal1",
                    "Translation": {"length": 900},
                },
                {
                    "id": "ENST_NONCODING",
                    "display_name": "ncrna",
                    "length": 2400,
                    "biotype": "lncRNA",
                    "is_canonical": 1,
                    "transcript_support_level": 1,
                    "appris": "principal1",
                },
            ]
        }
        choices = extract_transcript_choices(payload)
        best = choose_preferred_transcript(choices)
        self.assertIsNotNone(best)
        self.assertEqual(best.transcript_id, "ENST_CANON")

    def test_choose_preferred_transcript_uses_tsl_then_cds_then_length(self) -> None:
        payload = {
            "Transcript": [
                {
                    "id": "ENST_TSL2",
                    "display_name": "tsl2",
                    "length": 2600,
                    "biotype": "protein_coding",
                    "is_canonical": 0,
                    "transcript_support_level": "2",
                    "appris": "principal1",
                    "Translation": {"length": 1000},
                },
                {
                    "id": "ENST_TSL1",
                    "display_name": "tsl1",
                    "length": 2000,
                    "biotype": "protein_coding",
                    "is_canonical": 0,
                    "transcript_support_level": "1",
                    "appris": "principal1",
                    "Translation": {"length": 800},
                },
            ]
        }
        choices = extract_transcript_choices(payload)
        best = choose_preferred_transcript(choices)
        self.assertIsNotNone(best)
        self.assertEqual(best.transcript_id, "ENST_TSL1")


if __name__ == "__main__":
    unittest.main()

