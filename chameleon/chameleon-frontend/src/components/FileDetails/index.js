import React, { useContext, useState } from "react";
import { Wrapper, Heading } from "./styles";
import Radio from "@material-ui/core/Radio";
import RadioGroup from "@material-ui/core/RadioGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import { ChameleonContext } from "../../common/ChameleonContext";

export const FileDetails = () => {
    const [value, setValue] = useState("excel");
    const extensions = {
        excel: ".xlsx",
        geojson: ".geojson",
        csv: ".zip",
    };

    const { setFileName, setFileType } = useContext(ChameleonContext);

    const handleChange = (e) => {
        setValue(e.target.value);
        setFileType(e.target.value);
    };

    const inputChange = (e) => {
        setFileName(e.target.value);
    };

    return (
        <>
            <Wrapper>
                <Heading>File Details</Heading>
            </Wrapper>
            <div
                style={{
                    display: "grid",
                    justifyContent: "center",
                    alignItems: "center",
                    marginTop: "5%",
                }}
            >
                <label>
                    Output File Name:
                    <input
                        style={{ textAlign: "right" }}
                        type="text"
                        name="output"
                        placeholder="chameleon"
                        onChange={inputChange}
                    />
                    <span>{extensions[value]}</span>
                </label>

                <label>Format:</label>
                    <RadioGroup
                        aria-label="file_output"
                        name="file_format"
                        value={value}
                        onChange={handleChange}
                    >
                        <FormControlLabel
                            value="excel"
                            control={<Radio />}
                            label="Excel"
                        />
                        <FormControlLabel
                            value="geojson"
                            control={<Radio />}
                            label="GeoJSON"
                        />
                        <FormControlLabel
                            value="csv"
                            control={<Radio />}
                            label="CSV"
                        />
                    </RadioGroup>
            </div>
        </>
    );
};
