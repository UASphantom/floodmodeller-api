import plotly.graph_objects as go
import pandas as pd
from floodmodeller_api import ZZN
import csv
from pathlib import Path
import numpy as np
import os
import shutil


def test():
    gauge_locations_path = r"C:\FloodModellerJacobs\Calibration Data\GaugeList\GaugeListLocation.xlsx"
    variable = "Stage"
    models_path = r"C:\FloodModellerJacobs\Calibration Data\1DResults"
    event_data_folder_path = r"C:\FloodModellerJacobs\Calibration Data\EventData"
    output_folder = r"C:\FloodModellerJacobs\Calibration Data\output"
    c = Calibration()
    c.calibrate_node(
        gauge_locations_path,
        variable,
        models_path,
        event_data_folder_path,
        output_folder,
    )


class Calibration:
    def __init__(self) -> None:
        pass

    def calibrate_node(
        self,
        gauge_locations_path,
        variable,
        models_path,
        event_data_path,
        output_folder,
    ):
        self._read_nodes(gauge_locations_path)
        print("Read in node names")
        self._link_models_events()
        print("Linked models to events")
        self._set_zzn_stage(models_path, variable)
        print("Read in zzn files")
        model_data_list = self._model_data()
        print("Cleaned model data")
        event_data = self._event_data(event_data_path)
        print("Read in + cleaned event data")
        combined = self._combine_df(event_data, model_data_list)
        print("Combined all data")
        self._output_data(combined, output_folder)
        print("Finished")

    def _read_nodes(self, gauge_locations_path):
        gauges_nodes = pd.read_excel(gauge_locations_path)
        tabs = list(gauges_nodes["Tab"])
        nodes = list(gauges_nodes["Node"])

        self._node_dict = {}
        for i in range (0,len(nodes)):
            self._node_dict[nodes[i]] = tabs[i]

        self._nodes = list(self._node_dict.keys())

    def _link_models_events(self):
        self._model_event_links = [
            {
                "event name": "2007 November tidal",
                "event data": "November_2007_All_Levels.xlsx",
                "model results": "BROADLANDS_BECCLES_51_V01_MHWS_0_1PCT_W0_05_1080HRS.zzn",
            },
            {
                "event name": "2010 March fluvial",
                "event data": "March_2010_All_Levels.xlsx",
                "model results": "BROADLANDS_BECCLES_51_V01_MHWS_5PCT_1080HRS.zzn",
            },
            {
                "event name": "2013 December tidal",
                "event data": "December_2013_All_Levels.xlsx",
                "model results": "BROADLANDS_DESIGN_JACOBS_UPDATE_50_MHWS_1PCT.zzn",
            },
            {
                "event name": "2013 March fluvial",
                "event data": "March_2013_All_Levels.xlsx",
                "model results": "BROADLANDS_DESIGN_JACOBS_UPDATE_51_MHWS_0_5PCT_1080HRS.zzn",
            },
        ]

    def _set_zzn_stage(self, models_path, variable):
        self._model_names = []
        self._model_dfs = []
        for link in self._model_event_links:
            file = link["model results"]
            zzn = ZZN(Path(models_path, file))
            df = zzn.to_dataframe(variable=variable)
            self._model_names.append(file[:-4])
            self._model_dfs.append(df)

    def _model_data(self):
        model_data_list = []
        node_name_list = []
        for i, model_df in enumerate(self._model_dfs):
            model_nodes_list = []
            name_list = []
            for node in self._nodes:
                if node in model_df:
                    model_nodes_list.append(model_df[node])
                    name_list.append(f"{node}_{self._model_names[i]}")
            node_name_list.append(name_list)
            model_nodes_df = pd.concat(model_nodes_list, axis=1)
            model_data_list.append(model_nodes_df)
        return [model_data_list, node_name_list]

    def _event_data(self, event_data_path):
        xlsx_file_paths = []
        self._event_names = []
        for link in self._model_event_links:
            folder = link["event name"]
            file = link["event data"]
            file_path = str(Path(event_data_path, folder, file))
            xlsx_file_paths.append(file_path)
            self._event_names.append(folder)

        print("Found event data path")

        event_data_list = []
        index = 1
        for i, event in enumerate(self._event_names):
            for node in self._nodes:
                try:
                    sheet = pd.read_excel(
                        xlsx_file_paths[i], sheet_name=self._node_dict[node]
                    )
                    time = list(
                        filter(lambda x: x is not None, (list(sheet.iloc[:, 0])[13:]))
                    )
                    values = list(
                        filter(lambda x: x is not None, (list(sheet.iloc[:, 2])[13:]))
                    )
                    event_data_list.append(
                        pd.DataFrame(
                            {f"{node}_{event}": values},
                            index=pd.Index(time, name="Time (hr)"),
                        )
                    )
                    print(
                        f"Added {self._node_dict[node]} for {event}: {index}/{len(self._event_names) * len(self._nodes)}"
                    )
                except:
                    print(
                        f"Failed to add {self._node_dict[node]} for {event}: {index}/{len(self._event_names) * len(self._nodes)}"
                    )
                index += 1
                # workbook file can't be found, or node sheet can't be found
        return event_data_list

    def _combine_df(self, event_data, model_data):
        model_data_dfs = model_data[0]
        model_data_cols = model_data[1]
        for i, df in enumerate(model_data_dfs):
            df.columns = model_data_cols[i]

        model_df = pd.concat(model_data_dfs, axis=1)
        event_df = pd.concat(event_data, axis=1)

        # make them the dataframes the same length
        num_model_rows = len(model_df)
        num_event_rows = len(event_df)
        if num_model_rows != num_event_rows:
            if num_model_rows < num_event_rows:
                num_rows = num_model_rows
                event_df = event_df.head(num_rows)
            else:
                num_rows = num_event_rows
                model_df = model_df.head(num_rows)

        return [model_df, event_df]

    def _output_data(self, combined_data, output_folder):
        model_df = combined_data[0]
        event_df = combined_data[1]
        csv_list = [
            [
                "Gauge",
                "Event",
                "Model Peak",
                "Event Peak",
                "Peak Difference",
                "Model Peak Time",
                "Event Peak Time",
                "Peak Time Difference",
            ],
        ]
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)
        os.makedirs(Path(output_folder,"plots"))

        for node in self._nodes:
            node_model_mask = [col for col in model_df.columns if node in col]
            node_filtered_model = model_df[node_model_mask]
            node_event_mask = [col for col in event_df.columns if node in col]
            node_filtered_event = event_df[node_event_mask]

            if (
                len(node_filtered_model.columns) == 0
                or len(node_filtered_event.columns) == 0
            ):
                continue

            self._plot(node, node_filtered_model, node_filtered_event, output_folder)
            self._fill_csv_list(
                node, node_filtered_model, node_filtered_event, csv_list,
            )
        print("Plotted data")
        self._outputs_csv(csv_list, output_folder)
        print("Filled out csv data")

    def _plot(self, node, node_filtered_model, node_filtered_event, output_folder):
        fig = go.Figure()

        links = self._model_event_links
        fig.add_trace(
            go.Scatter(
                x=node_filtered_model.index,
                y=node_filtered_model[node_filtered_model.columns[0]],
                name="Model Data",
                mode="lines",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=node_filtered_event.index,
                y=node_filtered_event[node_filtered_event.columns[0]],
                name="Event Data",
                mode="lines",
            )
        )

        links_dropdown = []
        for link in self._model_event_links:
            model_col_name = f"{node}_{link['model results']}"[:-4]
            event_col_name = f"{node}_{link['event name']}"
            if (model_col_name) in node_filtered_model.columns and (event_col_name) in node_filtered_event.columns:
                model_data = node_filtered_model[f"{node}_{link['model results']}"[:-4]]
                event_data = node_filtered_event[f"{node}_{link['event name']}"]
                links_dropdown.append(
                    dict(
                        method="update",
                        label=link["event name"],
                        visible=True,
                        args=[{"y": [model_data, event_data]}],
                    )
                )

        # dropdown
        fig.update_layout(
            updatemenus=[
                dict(
                    buttons=links_dropdown,
                    direction="down",
                    name="Node",
                    x=-0.05,
                    y=1.1,
                ),
            ]
        )

        fig.update_layout(
            title={"text": f"{self._node_dict[node]}", "y": 0.95, "x": 0.5},
            xaxis_title="Time from start (hrs)",
            yaxis_title="Water level (m)",
        )

        fig.write_html(Path(output_folder, f"plots\\{self._node_dict[node]}.html"))

    def _fill_csv_list(self, node, node_filtered_model, node_filtered_event, csv_list):
        for link in self._model_event_links:
            model_col_name = f"{node}_{link['model results']}"[:-4]
            event_col_name = f"{node}_{link['event name']}"
            if (model_col_name) in node_filtered_model.columns and (event_col_name) in node_filtered_event.columns:
                model_col = (
                    node_filtered_model[f"{node}_{link['model results']}"[:-4]]
                ).replace("---", np.nan)
                event_col = (node_filtered_event[f"{node}_{link['event name']}"]).replace(
                    "---", np.nan
                )
                model_peak = model_col.max()
                event_peak = event_col.max()
                model_time_peak = model_col.idxmax()
                event_time_peak = event_col.idxmax()
                csv_list.append(
                    [
                        self._node_dict[node],
                        link["event name"],
                        model_peak,
                        event_peak,
                        f"{abs(model_peak - event_peak):.3f}",
                        model_time_peak,
                        event_time_peak,
                        f"{abs(model_time_peak - event_time_peak):.3f}",
                    ]
                )

    def _outputs_csv(self, csv_list, output_folder):
        with open(
            Path(output_folder, "Gauge_Peak_Data.csv"), "w", newline=""
        ) as csvfile:
            writer = csv.writer(csvfile, delimiter=",")
            for line in csv_list:
                writer.writerow(line)


test()
