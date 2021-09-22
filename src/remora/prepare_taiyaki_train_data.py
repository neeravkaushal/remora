import numpy as np
from tqdm import tqdm

from remora import log
from remora.data_chunks import get_motif_pos

LOGGER = log.get_logger()


def extract_canonical_dataset(
    input_msf, output_msf, context_bases, max_chunks_per_read
):
    LOGGER.info("Processing reads")
    num_reads = num_chunks = 0
    for read in tqdm(input_msf, smoothing=0):
        if read.Reference.size <= context_bases * 2:
            continue
        read_dict = read.get_read_dictionary()
        valid_size = read.Reference.size - (context_bases * 2)
        num_reads += 1
        for center_loc in np.random.choice(
            np.arange(context_bases, read.Reference.size - context_bases),
            size=min(max_chunks_per_read, valid_size),
            replace=False,
        ):
            chunk_dict = read_dict.copy()
            # trim signal and correct Ref_to_signal mapping
            ref_st = center_loc - context_bases
            ref_en = center_loc + context_bases + 1
            sig_st = read.Ref_to_signal[ref_st]
            sig_en = read.Ref_to_signal[ref_en]
            chunk_dict["read_id"] = f"{read.read_id}:::pos{center_loc}"
            chunk_dict["Dacs"] = read.Dacs[sig_st:sig_en]
            chunk_dict["Ref_to_signal"] = (
                read.Ref_to_signal[ref_st:ref_en] - sig_st
            )
            chunk_dict["Reference"] = read.Reference[
                center_loc - context_bases : center_loc + context_bases + 1
            ]
            num_chunks += 1
            output_msf.write_read(chunk_dict)
    LOGGER.info(f"Extracted {num_chunks} chunks from {num_reads} reads.")


def extract_modbase_dataset(
    input_msf,
    output_msf,
    mod_base,
    int_can_motif,
    motif_offset,
    context_bases,
    max_chunks_per_read,
):
    alphabet_info = input_msf.get_alphabet_information()

    int_mod_base = alphabet_info.alphabet.find(mod_base)
    int_mod_motif = np.concatenate(
        [
            int_can_motif[:motif_offset],
            [int_mod_base],
            int_can_motif[motif_offset + 1 :],
        ]
    )

    LOGGER.info("Processing reads")
    num_reads = num_chunks = 0
    for read in tqdm(input_msf, smoothing=0):
        # select motif based on modified base content of read
        int_motif = (
            int_mod_motif
            if (read.Reference == int_mod_base).sum() > 0
            else int_can_motif
        )
        # select a random hit to the motif
        motif_hits = get_motif_pos(read.Reference, int_motif)
        motif_hits = motif_hits[
            np.logical_and(
                motif_hits > context_bases,
                motif_hits < read.Reference.size - context_bases - 1,
            )
        ]
        if motif_hits.size == 0:
            continue
        num_reads += 1
        read_dict = read.get_read_dictionary()
        for motif_loc in np.random.choice(
            motif_hits,
            size=min(max_chunks_per_read, motif_hits.size),
            replace=False,
        ):
            chunk_dict = read_dict.copy()
            center_loc = motif_loc + motif_offset
            # trim signal and adjust Ref_to_signal mapping
            ref_st = center_loc - context_bases
            ref_en = center_loc + context_bases + 1
            sig_st = read.Ref_to_signal[ref_st]
            sig_en = read.Ref_to_signal[ref_en]
            # remove chunks with more signal than bases
            # TODO add more stringent filtering (maybe wait for
            # on-the-fly-chunk extraction)
            if sig_en - sig_st < ref_en - ref_st:
                continue
            chunk_dict["read_id"] = f"{read.read_id}:::pos{center_loc}"
            chunk_dict["Dacs"] = read.Dacs[sig_st:sig_en]
            chunk_dict["Ref_to_signal"] = (
                read.Ref_to_signal[ref_st:ref_en] - sig_st
            )
            chunk_dict["Reference"] = read.Reference[
                center_loc - context_bases : center_loc + context_bases + 1
            ]
            num_chunks += 1
            output_msf.write_read(chunk_dict)

    LOGGER.info(f"Extracted {num_chunks} chunks from {num_reads} reads.")