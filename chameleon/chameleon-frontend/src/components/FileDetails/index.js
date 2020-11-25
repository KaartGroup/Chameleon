import React, { useState } from "react";
import { Wrapper, Heading } from "./styles";
import Radio from "@material-ui/core/Radio";
import RadioGroup from "@material-ui/core/RadioGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import FormControl from "@material-ui/core/FormControl";
import FormLabel from "@material-ui/core/FormLabel";

export const FileDetails = () => {
    const [value, setValue] = useState("female");

    const handleChange = (event) => {
        setValue(event.target.value);
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
                    height: "37%",
                }}
            >
                <input
                    type="hidden"
                    className="high_deletions_ok"
                    disabled=""
                />
                <label>
                    {" "}
                    Output File Name:
                    <input
                        style={{ textAlign: "right" }}
                        type="text"
                        className="output"
                        placeholder="chameleon"
                    />
                    <span className="fileExt">.xlsx</span>
                </label>

                <FormControl component="fieldset">
                    <FormLabel component="legend">Format:</FormLabel>
                    <RadioGroup
                        aria-label="file_output"
                        name="output"
                        value={value}
                        onChange={handleChange}
                    >
                        <FormControlLabel
                            value="female"
                            control={<Radio />}
                            label="Excel"
                        />
                        <FormControlLabel
                            value="male"
                            control={<Radio />}
                            label="GeoJSON"
                        />
                        <FormControlLabel
                            value="other"
                            control={<Radio />}
                            label="CSV"
                        />
                    </RadioGroup>
                </FormControl>
            </div>
        </>
    );
};
