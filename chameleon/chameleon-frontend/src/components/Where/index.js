import React from "react";
import { Wrapper, Heading } from "./styles";

export const Where = () => {
    return (
        <>
            <Wrapper>
                <Heading> Where </Heading>
            </Wrapper>
            <div
                style={{
                    display: "grid",
                    justifyContent: "center",
                    alignItems: "center",
                }}
            >
                <p
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        fontSize: "12px",
                    }}
                >
                    2 Letter{" "}
                    <u style={{ paddingRight: "3px", paddingLeft: "3px" }}>
                        ISO
                    </u>{" "}
                    Country Code:
                </p>
                <input
                    type="text"
                    placeholder="ISO Code"
                    onChange={() => console.log("handling ISO Code change")}
                />
            </div>
        </>
    );
};
