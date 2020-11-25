import React, { useState } from "react";
import {
    Wrapper,
    Heading,
} from "./styles";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

export const When = () => {
    const [startDate, setStartDate] = useState(new Date());

    return (
        <div>
            <Heading> When </Heading>
            <p style={{ display: "flex", justifyContent: "center", fontSize: "12px" }}>Start Date:</p>
                <DatePicker selected={startDate} onChange={date => setStartDate(date)} />
            <br></br>
            <p style={{ display: "flex", justifyContent: "center", fontSize: "12px" }}>End Date:</p>
                <DatePicker selected={startDate} onChange={date => setStartDate(date)} />
        </div>
        
    );
};