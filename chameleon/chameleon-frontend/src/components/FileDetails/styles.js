import styled from "styled-components";

export const Wrapper = styled.div`
    display: flex;
    border-bottom: 1px solid black;
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

export const FormWrapper = styled.div`
display: "grid",
justifyContent: "center",
alignItems: "center",
marginTop: "5%",
`;

export const FileDetailsInput = styled.input`
  padding: 12px 20px;
  margin: 8px 0;
  display: inline-block;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
`;

export const Label = styled.p`
font-size: 15px;
`;

export const FolderIMG = styled.img`
height: 19px;
color: #f4753c;
`;