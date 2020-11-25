import React from "react";
import {
    Wrapper,
    Heading,
    StyledLabel,
} from "./styles";

export const How = () => {
    return (
      <div>
        <Heading> How </Heading>
        <StyledLabel> 
          Tag: 
          <input type="text" placeholder="OSM Key" onChange={() => console.log('handling Tag change')} />
        </StyledLabel>

        <br></br>
        <br></br>
        
        <button onClick={() => console.log('add')}>Add</button>
        <button onClick={() => console.log('remove')}>Remove</button>
        <button onClick={() => console.log('clear')}>Clear</button>
        <select size="5" multiple=""></select>

        <br></br>
        <br></br>
      </div>
    );
};