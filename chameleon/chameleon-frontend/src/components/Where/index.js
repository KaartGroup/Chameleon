import React, { useContext } from "react";
import { Wrapper, Heading } from "./styles";
import { ChameleonContext } from "../../common/ChameleonContext"; 

// TODO verify input is Alpha letters only
// TODO maybe autocomplete list?
// TODO styling
export const Where = () => {
    const { setWhere } = useContext(ChameleonContext);
    
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
                    name="location"
                    maxLength={2}
                    onChange={(e) => { setWhere(e.target.value) } }
                />
            </div>
        </>
    );
};
