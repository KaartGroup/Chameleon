import React from "react";
import {
    Wrapper,
    Heading,
} from "./styles";

export const FileDetails = () => {
    return (
        <div>
            <Heading>File Details</Heading>
            <input type="hidden" className="high_deletions_ok" disabled="" />
                <label> Output File Name:
                    <input style={{ textAlign: "right" }} type="text" className="output" placeholder="chameleon" /><span className="fileExt">.xlsx</span>
                </label>
                
                <br></br>
                
                    <p style={{ textAlign: "center" }}>File Format:</p>

                <br></br>
                <label>Excel
                    <input value="excel" type="radio" className="file_format" defaultChecked="" />
                </label>
                <label>GeoJSON
                    <input value="geojson" type="radio" className="file_format" defaultChecked="" />
                </label>
                <label>CSV
                    <input value="csv" type="radio" className="file_format" defaultChecked="" />
                </label>
        </div>
    );
}
