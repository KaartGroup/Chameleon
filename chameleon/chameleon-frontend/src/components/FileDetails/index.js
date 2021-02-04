import React, { useContext, useState } from "react";
import { Wrapper, Heading, FileDetailsInput, FormWrapper, Label, FolderIMG } from "./styles";
import Radio from "@material-ui/core/Radio";
import RadioGroup from "@material-ui/core/RadioGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import { ChameleonContext } from "../../common/ChameleonContext";
import folder from "../../images/folder.svg"; 
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
                <Heading>
                    File Details<FolderIMG src={folder} alt="where IMG"/>
                </Heading>
            </Wrapper>
            <FormWrapper>
                <Label>
                    Output File Name:
                    <FileDetailsInput
                        type="text"
                        name="output"
                        placeholder="chameleon"
                        onChange={inputChange}
                    />
                    <span>{extensions[value]}</span>
                    </Label>
                <Label>Format:</Label>
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
            </FormWrapper>
        </>
    );
};
