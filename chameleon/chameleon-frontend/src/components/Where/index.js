import React from "react";
import {
    Wrapper,
    Heading,
} from "./styles";

export const Where = () => {
    return (
        <div>
            <Heading> Where </Heading>
            <p style={{ display: "flex", justifyContent: "center", fontSize: "12px" }}>2 Letter <u style={{ paddingRight: "3px", paddingLeft: "3px"}}>ISO</u> Country Code:</p>
            <input type="text" placeholder="ISO Code" onChange={() => console.log('handling ISO Code change')} />
        </div>
    );
};