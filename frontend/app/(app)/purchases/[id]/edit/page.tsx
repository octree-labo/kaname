import { DocumentEditPage } from "@/components/document/DocumentEditPage";
import { purchasesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentEditPage config={purchasesModule} />;
}
