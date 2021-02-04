import React, { useContext } from "react";
import { Wrapper, Heading, WhereInput, FormWrapper, Label, WhereIMG } from "./styles";
import { ChameleonContext } from "../../common/ChameleonContext";
import whereIMG from "../../images/whereIMG.svg"; 
// TODO verify input is Alpha letters only
// TODO maybe autocomplete list?
// TODO styling
export const Where = () => {
    const { setWhere, where } = useContext(ChameleonContext);
    
    return (
        <>
            <Wrapper>
            <Heading>
                Where<WhereIMG src={whereIMG} alt="where IMG"/>
            </Heading>
            </Wrapper>
            <FormWrapper>
                <Label>
                    2 Letter{" "}
                    <u style={{ paddingRight: "3px", paddingLeft: "3px" }}>
                        ISO
                    </u>{" "}
                    Country Code:
                <WhereInput
                    type="text"
                    placeholder="ISO Code"
                    name="location"
                    value={where}
                    maxLength={2}
                    onChange={(e) => { setWhere(e.target.value) } }
                />
                </Label>
            </FormWrapper>
        </>
    );
};

// {!confirmationFailed && (
//     <Text>
//       <Caution>&#x26A0; </Caution>The passwords do not match
//     </Text>
//   )}