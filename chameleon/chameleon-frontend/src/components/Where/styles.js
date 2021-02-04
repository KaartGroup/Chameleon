import styled from "styled-components";

export const Wrapper = styled.div`
    display: flex;
    border-bottom: 1px solid black;
    // background: #f4753c;
`;

export const Heading = styled.p`
    display: flex;
    font-family: "Hind Guntur",sans-serif;
    width: 100%;
    font-size: 20px;
    font-weight: bold;
    justify-content: center;
    align-items: center;
    text-decoration: underline #f4753c;
`;

export const WhereInput = styled.input`
  padding: 12px 20px;
  margin: 8px 8px;
  display: inline-block;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
`;

export const FormWrapper = styled.div`
display: grid;
justify-content: center;
align-items: center;
`;

export const Label = styled.p`
font-size: 15px;
`;

export const Caution = styled.div`
  display: inline-block;
  transform: translate(0%, 3%);
  bottom: 0px;
`;

export const WhereIMG = styled.img`
height: 19px;
`;