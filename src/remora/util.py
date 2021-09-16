import torch
import os
from os.path import join, isfile, exists
import pandas as pd
from remora import log

LOGGER = log.get_logger()


def save_checkpoint(state, out_path):
    if not exists(out_path):
        os.makedirs(out_path)
    filename = join(out_path, f"{state['model_name']}_{state['epoch']}.tar")
    torch.save(state, filename)


def continue_from_checkpoint(dir_path, training_var=None, **kwargs):
    if not exists(dir_path):
        return

    all_ckps = [
        f
        for f in os.listdir(dir_path)
        if isfile(join(dir_path, f)) and ".tar" in f
    ]
    if all_ckps == []:
        return

    ckp_path = join(dir_path, max(all_ckps))

    LOGGER.info(f"Continuing training from {ckp_path}")

    ckp = torch.load(ckp_path)

    for key, value in kwargs.items():
        if key in ckp:
            try:
                value.load_state_dict(ckp[key])
            except AttributeError:
                continue

    if training_var is not None:
        for var in training_var:
            if var in ckp:
                training_var[var] = ckp[var]


class resultsWriter:
    def __init__(self, output_path):
        self.output_path = output_path
        column_names = ["Read ID", "Position", "Mod Score"]
        df = pd.DataFrame(columns=column_names)
        df.to_csv(self.output_path, sep="\t")

    def write(self, results_table):
        with open(self.output_path, "a") as f:
            results_table.to_csv(f, header=f.tell() == 0)


class plotter:
    def __init__(self, outdir):
        self.outdir = outdir
        self.losses = []
        self.accuracy = []

    def append_result(self, accuracy, loss):
        self.losses.append(loss)
        self.accuracy.append(accuracy)

    def save_plots(self):
        import matplotlib.pyplot as plt

        fig1 = plt.figure()
        ax1 = plt.subplot(111)
        ax1.plot(list(range(len(self.accuracy))), self.accuracy)
        ax1.set_ylabel("Validation accuracy")
        ax1.set_xlabel("Epochs")

        fig2 = plt.figure()
        ax2 = plt.subplot(111)
        ax2.plot(list(range(len(self.losses))), self.losses)
        ax2.set_ylabel("Validation loss")
        ax2.set_xlabel("Epochs")

        if not os.path.isdir(self.outdir):
            os.mkdir(self.outdir)

        fig1.savefig(os.path.join(self.outdir, "accuracy.png"), format="png")
        fig2.savefig(os.path.join(self.outdir, "loss.png"), format="png")
